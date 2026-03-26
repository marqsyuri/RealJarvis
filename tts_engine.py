"""
tts_engine.py — ElevenLabs TTS com pygame (MP3, Windows-friendly)

Abordagem:
  - Busca MP3 da ElevenLabs via httpx (sem PCM manual = sem problema de sample rate)
  - Toca com pygame.mixer que suporta MP3 nativo no Windows
  - Fila serializada (uma fala de cada vez)
  - is_speaking flag para mute automático do microfone

Latência: ~300-500ms (busca + init mixer) — sem chiado, sem static.
"""
import io
import time
import threading
import queue as q_module

import httpx
import pygame

import config


class TTSEngine:
    def __init__(self):
        pygame.mixer.init()
        self._queue: q_module.Queue = q_module.Queue()
        self._speaking = threading.Event()
        self._worker = threading.Thread(target=self._run, daemon=True, name="tts-worker")
        self._worker.start()

    # ── API pública ──────────────────────────────────────────────────

    @property
    def is_speaking(self) -> bool:
        """True enquanto áudio está tocando. Usado para mute do microfone."""
        return self._speaking.is_set()

    def speak(self, text: str):
        """Enfileira fala. Retorna imediatamente (não-bloqueante)."""
        if text and text.strip():
            self._queue.put((text, None))

    def speak_wait(self, text: str):
        """Enfileira fala e BLOQUEIA até terminar.
        Usar para 'Sim, senhor?' antes de capturar o próximo comando."""
        if not text or not text.strip():
            return
        done = threading.Event()
        self._queue.put((text, done))
        done.wait()

    # ── Loop interno ─────────────────────────────────────────────────

    def _run(self):
        while True:
            text, done_event = self._queue.get()
            self._speaking.set()
            try:
                self._say(text)
            except Exception as e:
                print(f"❌ [TTS] {type(e).__name__}: {e}")
            finally:
                self._speaking.clear()
                if done_event:
                    done_event.set()
                self._queue.task_done()

    def _say(self, text: str):
        """Busca MP3 da ElevenLabs e toca com pygame.mixer."""
        short = text[:80] + "…" if len(text) > 80 else text
        print(f"🔊 [TTS] {short}")

        if not config.ELEVENLABS_API_KEY:
            print("⚠️  [TTS] ELEVENLABS_API_KEY não configurada — sem áudio")
            return

        url = (
            f"https://api.elevenlabs.io/v1/text-to-speech"
            f"/{config.ELEVENLABS_VOICE_ID}"
        )
        headers = {
            "xi-api-key": config.ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        }
        body = {
            "text": text,
            "model_id": config.ELEVENLABS_MODEL,
            "output_format": "mp3_44100_128",   # MP3 nativo — pygame lida perfeitamente
            "voice_settings": {
                "stability": 0.45,
                "similarity_boost": 0.80,
                "style": 0.05,
                "use_speaker_boost": True,
            },
        }

        resp = httpx.post(url, headers=headers, json=body, timeout=30.0)
        resp.raise_for_status()

        # Tocar MP3 direto do buffer em memória (sem arquivo temporário)
        audio_buf = io.BytesIO(resp.content)
        pygame.mixer.music.load(audio_buf)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
