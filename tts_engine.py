"""
tts_engine.py — ElevenLabs TTS com streaming PCM e fila serializada

Fluxo:
  speak(text)     → enfileira (não-bloqueante)
  speak_wait(text)→ enfileira e bloqueia até a fala terminar
  is_speaking     → True enquanto áudio está tocando (usado para mute do mic)

Implementação usa httpx streaming + pyaudio para tocar PCM em tempo real.
A fala começa no primeiro chunk (~100ms) sem esperar o áudio completo.
"""
import threading
import queue as q_module

import httpx
import pyaudio

import config


class TTSEngine:
    def __init__(self):
        self._queue: q_module.Queue = q_module.Queue()
        self._speaking = threading.Event()
        self._pa = pyaudio.PyAudio()
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
        Usar para respostas onde precisamos esperar antes de continuar
        (ex: 'Sim, senhor?' antes de capturar o próximo comando)."""
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
                self._stream_pcm(text)
            except Exception as e:
                print(f"❌ [TTS] {type(e).__name__}: {e}")
            finally:
                self._speaking.clear()
                if done_event:
                    done_event.set()
                self._queue.task_done()

    def _stream_pcm(self, text: str):
        """Streaming PCM da ElevenLabs → pyaudio. Latência ~100ms."""
        short = text[:80] + "…" if len(text) > 80 else text
        print(f"🔊 [TTS] {short}")

        if not config.ELEVENLABS_API_KEY:
            print("⚠️  [TTS] ELEVENLABS_API_KEY não configurada — sem áudio")
            return

        url = (
            f"https://api.elevenlabs.io/v1/text-to-speech"
            f"/{config.ELEVENLABS_VOICE_ID}/stream"
        )
        headers = {
            "xi-api-key": config.ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        }
        body = {
            "text": text,
            "model_id": config.ELEVENLABS_MODEL,
            "output_format": config.ELEVENLABS_OUTPUT_FORMAT,
            "voice_settings": {
                "stability": 0.45,
                "similarity_boost": 0.80,
                "style": 0.05,
                "use_speaker_boost": True,
            },
        }

        # pyaudio: mais confiável no Windows para PCM direto
        pa_stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=config.ELEVENLABS_SAMPLE_RATE,
            output=True,
            frames_per_buffer=4096,
        )
        try:
            with httpx.stream("POST", url, headers=headers, json=body, timeout=30.0) as resp:
                resp.raise_for_status()
                remainder = b""
                for chunk in resp.iter_bytes(4096):
                    if not chunk:
                        continue
                    # Garantir múltiplo de 2 bytes (int16)
                    chunk = remainder + chunk
                    remainder = b""
                    if len(chunk) % 2 != 0:
                        remainder = chunk[-1:]
                        chunk = chunk[:-1]
                    if chunk:
                        pa_stream.write(chunk)
        finally:
            pa_stream.stop_stream()
            pa_stream.close()
