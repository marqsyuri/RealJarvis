"""
task_manager.py — Pool async de tarefas paralelas com fila TTS

Fluxo:
  submit(text) → cria asyncio.Task imediatamente, retorna task_id
  _run()       → aguarda semaphore (max MAX_BRAIN_WORKERS concorrentes)
               → chama ask_brain() em ThreadPoolExecutor (não bloqueia event loop)
               → enfileira resultado na TTS (não-bloqueante)

Múltiplos comandos podem ser processados em paralelo.
A TTS serializa as respostas na ordem de chegada.
"""
import asyncio
import concurrent.futures
import uuid
from typing import TYPE_CHECKING

from brain_client import ask_brain

if TYPE_CHECKING:
    from tts_engine import TTSEngine


class TaskManager:
    def __init__(self, tts: "TTSEngine", max_workers: int = 3):
        self.tts = tts
        self.semaphore = asyncio.Semaphore(max_workers)
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="brain-worker",
        )
        self._active: int = 0

    async def submit(self, text: str) -> str:
        """Submete tarefa em background. Retorna task_id imediatamente."""
        task_id = uuid.uuid4().hex[:6]
        label = text[:50] + "…" if len(text) > 50 else text
        print(f"📋 [Task:{task_id}] '{label}'")
        asyncio.create_task(self._run(task_id, text))
        return task_id

    @property
    def active_count(self) -> int:
        return self._active

    async def _run(self, task_id: str, text: str):
        async with self.semaphore:
            self._active += 1
            loop = asyncio.get_running_loop()
            try:
                print(f"⚡ [Task:{task_id}] Enviando ao cérebro... (ativas: {self._active})")
                result = await loop.run_in_executor(self.executor, ask_brain, text)
                print(f"✅ [Task:{task_id}] Resposta pronta ({len(result)} chars)")
                self.tts.speak(result)  # enfileira na TTS (não-bloqueante)
            except Exception as e:
                print(f"❌ [Task:{task_id}] {type(e).__name__}: {e}")
                self.tts.speak("Desculpe, não consegui completar essa tarefa, senhor.")
            finally:
                self._active -= 1
