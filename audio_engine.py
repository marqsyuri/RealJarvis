"""
audio_engine.py — Microfone com modo conversa + wake word

MODO WAKE WORD (padrão):
  Aguarda "Jarvis". Ao ouvir:
  - "Jarvis <comando>" → pling + processa + entra no modo conversa
  - "Jarvis" sozinho   → "Sim?" + entra no modo conversa

MODO CONVERSA (após ativação):
  Escuta livremente sem precisar dizer "Jarvis" de novo.
  Sai automaticamente após silêncio de ~3s.
  Sai com frases de encerramento ("pode ir", "tchau", "obrigado", etc.)
  Mute automático enquanto TTS fala (evita feedback loop).
"""
import asyncio
import time
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

        # Estado do modo conversa
        self._in_conversation = False
        self._silence_count = 0

    async def run(self):
        self._loop = asyncio.get_running_loop()
        await self._loop.run_in_executor(None, self._mic_loop)

    def _mic_loop(self):
        with sr.Microphone() as source:
            print("[Audio] Calibrando ruido ambiente...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
            print(f"[Audio] Aguardando wake word: '{config.WAKE_WORD}'...")

            while self.is_listening:
                # ── Mute: não capturar enquanto TTS toca ─────────────
                if self.tts.is_speaking:
                    time.sleep(0.1)
                    # Resetar contador de silêncio — TTS não é "silêncio do usuário"
                    self._silence_count = 0
                    continue

                # ── Escutar ──────────────────────────────────────────
                timeout = 1 if not self._in_conversation else 1
                try:
                    audio = self.recognizer.listen(
                        source,
                        timeout=timeout,
                        phrase_time_limit=config.PHRASE_LIMIT,
                    )
                    self._silence_count = 0  # ouviu algo → resetar silêncio
                except sr.WaitTimeoutError:
                    if self._in_conversation:
                        self._silence_count += 1
                        if self._silence_count >= config.CONVERSATION_SILENCE_TIMEOUTS:
                            self._exit_conversation()
                    continue

                if self.tts.is_speaking:
                    continue

                # ── Transcrever ──────────────────────────────────────
                try:
                    text = self.recognizer.recognize_google(
                        audio, language=config.STT_LANGUAGE
                    ).lower()
                except sr.UnknownValueError:
                    continue
                except Exception as e:
                    print(f"[STT Error] {type(e).__name__}: {e}")
                    continue

                # ── Roteamento ───────────────────────────────────────
                if self._in_conversation:
                    self._handle_conversation(text)
                else:
                    self._handle_wake_word(text)

    # ── Modo Wake Word ────────────────────────────────────────────────

    def _handle_wake_word(self, text: str):
        if config.WAKE_WORD not in text:
            return

        comando = text.replace(config.WAKE_WORD, "").strip()

        if not comando:
            # "Jarvis" sozinho → entrar no modo conversa
            self._enter_conversation()
            self.tts.speak_wait("Sim?")
        else:
            # "Jarvis, <comando>" → entrar no modo conversa + processar
            print(f"[Wake] comando detectado ({len(comando)} chars)")
            self._enter_conversation()
            self.tts.pling()
            self._submit(comando)

    # ── Modo Conversa ─────────────────────────────────────────────────

    def _handle_conversation(self, text: str):
        self._silence_count = 0

        # Frases de encerramento
        if any(phrase in text for phrase in config.CONVERSATION_EXIT_PHRASES):
            self._exit_conversation()
            self._submit(text)  # Haiku vai dar um "até logo" natural
            return

        # Comando normal em modo conversa
        print(f"[Conversa] ({len(text)} chars)")
        self.tts.pling()
        self._submit(text)

    # ── Helpers ───────────────────────────────────────────────────────

    def _enter_conversation(self):
        self._in_conversation = True
        self._silence_count = 0
        print("[Audio] Modo conversa ATIVO")

    def _exit_conversation(self):
        self._in_conversation = False
        self._silence_count = 0
        print("[Audio] Modo conversa encerrado -> aguardando wake word")

    def _submit(self, text: str):
        if not self._loop:
            return
        asyncio.run_coroutine_threadsafe(
            self.task_manager.submit(text),
            self._loop,
        )
