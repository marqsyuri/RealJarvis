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
import math
import os
import struct
import tempfile
import time
import threading
import queue as q_module

import httpx
import pygame

# Suprimir o banner "Hello from the pygame community" no console
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import config


def _generate_pling_wav(
    freq: float = 960,
    duration: float = 0.12,
    sample_rate: int = 44100,
    volume: float = 0.35,
) -> io.BytesIO:
    """Gera um 'pling' (sine com decay exponencial) como WAV em memória.
    Pure Python — sem numpy, sem deps extras.
    """
    n = int(duration * sample_rate)
    samples = []
    for i in range(n):
        t = i / sample_rate
        envelope = math.exp(-t * 18)          # decay rápido
        val = math.sin(2 * math.pi * freq * t) * envelope * volume
        samples.append(max(-32768, min(32767, int(val * 32767))))

    data_size = n * 2  # 16-bit mono
    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + data_size))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<I", 16))           # chunk size
    buf.write(struct.pack("<HH", 1, 1))        # PCM, mono
    buf.write(struct.pack("<II", sample_rate, sample_rate * 2))
    buf.write(struct.pack("<HH", 2, 16))       # block align, bits
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    for s in samples:
        buf.write(struct.pack("<h", s))
    buf.seek(0)
    return buf


class TTSEngine:
    def __init__(self):
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        self._queue: q_module.Queue = q_module.Queue()
        self._speaking = threading.Event()
        # Pré-carregar pling na inicialização
        self._pling_sound = pygame.mixer.Sound(_generate_pling_wav())
        self._worker = threading.Thread(target=self._run, daemon=True, name="tts-worker")
        self._worker.start()

    # ── API pública ──────────────────────────────────────────────────

    def pling(self):
        """Toca o som de confirmação (walkie-talkie). Não bloqueante."""
        self._pling_sound.play()

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
                # Evita emojis/ícones no Windows (console cp1252) para não quebrar encoding
                print(f"[TTS] ERROR {type(e).__name__}: {e}")
            finally:
                self._speaking.clear()
                if done_event:
                    done_event.set()
                self._queue.task_done()

    def _say(self, text: str):
        """Busca MP3 da ElevenLabs e toca com pygame.mixer."""
        # Não printar o texto — Windows Narrator leria em voz alta
        print(f"[TTS] ({len(text)} chars)")

        if not config.ELEVENLABS_API_KEY:
            print("[TTS] ELEVENLABS_API_KEY não configurada - sem áudio")
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
            "language_code": "pt",              # FORÇAR português — sem isso o modelo auto-detecta e mistura
            "output_format": "mp3_44100_128",   # MP3 nativo — pygame lida perfeitamente
            "voice_settings": {
                "stability": 0.50,
                "similarity_boost": 0.85,
                "style": 0.00,                  # style=0 = mais natural e menos "embolado"
                "use_speaker_boost": True,
            },
        }

        resp = httpx.post(url, headers=headers, json=body, timeout=30.0)
        resp.raise_for_status()

        # Salvar em arquivo temporário — mais confiável no Windows que BytesIO
        # (evita o buffer ser liberado antes do pygame terminar de ler)
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        try:
            tmp.write(resp.content)
            tmp.close()
            pygame.mixer.music.stop()          # garantir que não há nada tocando
            pygame.mixer.music.load(tmp.name)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
        finally:
            try:
                os.unlink(tmp.name)            # limpar temp após reprodução
            except OSError:
                pass
