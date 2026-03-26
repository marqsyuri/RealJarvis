"""
audio_engine.py — Loop de microfone com wake word, mute durante TTS e multi-task

Comportamento:
  - Escuta continuamente aguardando wake word (config.WAKE_WORD)
  - Durante TTS (is_speaking=True): descarta áudio capturado (evita feedback)
  - "Jarvis" sozinho → fala "Sim, senhor?" e escuta próximo comando
  - "Jarvis <comando>" → fala "Entendido, processando..." e submete ao TaskManager
  - Mic CONTINUA escutando enquanto o cérebro processa em background
  - Múltiplos comandos podem ser enfileirados sem bloquear o microfone
"""
import asyncio
import speech_recognition as sr
from typing import TYPE_CHECKING

import config

if TYPE_CHECKING:
    from tts_engine import TTSEngine
    from task_manager import TaskManager


class AudioEngine:
    def __init__(self, task_manager: "TaskManager", tts: "TTSEngine"):
        self.task_manager = task_manager
        self.tts = tts
        self.recognizer = sr.Recognizer()
        self.is_listening = True
        self._loop: asyncio.AbstractEventLoop | None = None

    # ── Ponto de entrada ─────────────────────────────────────────────

    async def run(self):
        """Inicia o loop de microfone. Bloqueia até is_listening=False."""
        self._loop = asyncio.get_running_loop()
        # Roda o loop bloqueante em thread separada para não travar o event loop
        await self._loop.run_in_executor(None, self._mic_loop)

    # ── Loop de microfone (thread dedicada) ──────────────────────────

    def _mic_loop(self):
        with sr.Microphone() as source:
            print("🎙️  [Jarvis] Calibrando ruído ambiente...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
            print(f"🎙️  [Jarvis] Aguardando wake word: '{config.WAKE_WORD}'...")

            while self.is_listening:
                try:
                    # ── Aguardar TTS terminar ANTES de capturar ──────────
                    # Evita que o mic capture o áudio do speaker (feedback loop)
                    if self.tts.is_speaking:
                        import time as _t
                        _t.sleep(0.1)
                        continue

                    audio = self.recognizer.listen(
                        source,
                        timeout=config.LISTEN_TIMEOUT,
                        phrase_time_limit=config.PHRASE_LIMIT,
                    )

                    # Dupla verificação: descartar se TTS começou durante captura
                    if self.tts.is_speaking:
                        continue

                    text = self.recognizer.recognize_google(
                        audio, language=config.STT_LANGUAGE
                    ).lower()

                    if config.WAKE_WORD not in text:
                        continue

                    # ── Wake word detectado ───────────────────────────
                    comando = text.replace(config.WAKE_WORD, "").strip()

                    if not comando:
                        # "Jarvis" sozinho → pede o comando
                        self.tts.speak_wait("Sim, senhor?")
                        try:
                            audio2 = self.recognizer.listen(
                                source,
                                timeout=5,
                                phrase_time_limit=config.PHRASE_LIMIT,
                            )
                            comando = self.recognizer.recognize_google(
                                audio2, language=config.STT_LANGUAGE
                            )
                        except (sr.WaitTimeoutError, sr.UnknownValueError):
                            continue

                    if not comando:
                        continue

                    print(f"\n🗣️  [Wake] detectado ({len(comando)} chars)")

                    # Submit em background (não bloqueia)
                    asyncio.run_coroutine_threadsafe(
                        self.task_manager.submit(comando),
                        self._loop,
                    )

                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    continue
                except Exception as e:
                    print(f"❌ [STT] {type(e).__name__}: {e}")
