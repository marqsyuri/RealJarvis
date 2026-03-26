"""
task_manager.py — Orquestrador de tarefas em 2 camadas

Fluxo por comando de voz:
  1. Chama Haiku (fast, ~400ms) → HaikuResult
  2. Fala a resposta imediata via TTS
  3. Se Haiku delegou ao Dexter: dispara tarefa em background
  4. Quando Dexter responde: fala o resultado

Múltiplos comandos podem estar em diferentes estágios ao mesmo tempo.
Haiku e Dexter rodam em ThreadPoolExecutors separados para não bloquear.
"""
import asyncio
import concurrent.futures
import uuid
from typing import TYPE_CHECKING

from brain_haiku import ask_haiku
from brain_dexter import ask_dexter

if TYPE_CHECKING:
    from tts_engine import TTSEngine


class TaskManager:
    def __init__(self, tts: "TTSEngine", max_workers: int = 3):
        self.tts = tts
        # Haiku: chamadas rápidas, mais workers
        self.haiku_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="haiku"
        )
        # Dexter: chamadas pesadas, workers separados
        self.dexter_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="dexter"
        )
        self.haiku_semaphore = asyncio.Semaphore(max_workers)
        self.dexter_semaphore = asyncio.Semaphore(max_workers)

    async def submit(self, text: str) -> str:
        """Envia comando. Retorna task_id imediatamente."""
        task_id = uuid.uuid4().hex[:6]
        label = text[:50] + "…" if len(text) > 50 else text
        print(f"📋 [Task:{task_id}] '{label}'")
        asyncio.create_task(self._run(task_id, text))
        return task_id

    async def _run(self, task_id: str, text: str):
        loop = asyncio.get_running_loop()

        # ── Etapa 1: Haiku (rápido) ───────────────────────────────
        async with self.haiku_semaphore:
            try:
                print(f"⚡ [Haiku:{task_id}] Processando...")
                result = await loop.run_in_executor(
                    self.haiku_executor, ask_haiku, text
                )
                print(f"✅ [Haiku:{task_id}] ok ({len(result.immediate_response)} chars)")
            except Exception as e:
                print(f"❌ [Haiku:{task_id}] {type(e).__name__}: {e}")
                self.tts.speak("Desculpe, tive um problema ao processar.")
                return

        # ── Etapa 2: Falar resposta imediata ─────────────────────
        self.tts.speak(result.immediate_response)

        # ── Etapa 3: Dexter em background (se necessário) ─────────
        if result.dexter_task:
            asyncio.create_task(self._run_dexter(task_id, result.dexter_task))

    async def _run_dexter(self, task_id: str, task: str):
        loop = asyncio.get_running_loop()
        async with self.dexter_semaphore:
            try:
                label = task[:60] + "…" if len(task) > 60 else task
                print(f"🧠 [Dexter:{task_id}] '{label}'")
                answer = await loop.run_in_executor(
                    self.dexter_executor, ask_dexter, task
                )
                print(f"✅ [Dexter:{task_id}] ok ({len(answer)} chars)")
                self.tts.speak(answer)
            except Exception as e:
                print(f"❌ [Dexter:{task_id}] {type(e).__name__}: {e}")
                self.tts.speak("Não consegui completar a tarefa no servidor.")
