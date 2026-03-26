"""
main.py — Jarvis Worker v2

Stack:
  IoTBridge    → WebSocket OpenClaw (node-host, comandos IoT push)
  TTSEngine    → ElevenLabs streaming PCM via sounddevice
  TaskManager  → Pool async (MAX_BRAIN_WORKERS paralelos)
  AudioEngine  → Microfone + wake word + mute durante TTS
"""
import asyncio
import sys
import os

# ── Redirecionar output para arquivo de log (evita Windows Narrator ler o console)
# Para ver logs em tempo real: type jarvis.log  ou  tail -f jarvis.log (Git Bash)
_log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis.log")
# Avisar no terminal original antes de silenciar o stdout
sys.__stdout__.write(f"[Jarvis] Iniciando... logs em: {_log_path}\n")
sys.__stdout__.flush()
_log_file = open(_log_path, "w", buffering=1, encoding="utf-8")
sys.stdout = _log_file
sys.stderr = _log_file

import config
from iot_bridge import IoTBridge
from tts_engine import TTSEngine
from task_manager import TaskManager
from audio_engine import AudioEngine


async def main():
    print("=" * 55)
    print("  J.A.R.V.I.S  -  Jarvis Worker v2")
    print("=" * 55)
    print(f"  Gateway : {config.GATEWAY_WS}")
    print(f"  Worker  : {config.WORKER_ID}")
    print(f"  Wake    : '{config.WAKE_WORD}'")
    print(f"  Tasks   : {config.MAX_BRAIN_WORKERS} paralelas")
    print(f"  TTS     : ElevenLabs {config.ELEVENLABS_MODEL}")
    print(f"  Voice   : {config.ELEVENLABS_VOICE_ID}")
    if not config.ELEVENLABS_API_KEY:
        print("  [Main] ELEVENLABS_API_KEY não definida - TTS desativado")
    print("=" * 55)

    # ── Montar stack ────────────────────────────────────────────────
    tts      = TTSEngine()
    task_mgr = TaskManager(tts, max_workers=config.MAX_BRAIN_WORKERS)
    bridge   = IoTBridge()
    audio    = AudioEngine(task_mgr, tts)

    # Injetar TTS na bridge para fluxo inverso (Dexter → fala no notebook)
    bridge.set_tts(tts)

    # ── IoT Bridge em background ────────────────────────────────────
    bridge.start()

    # ── Boas-vindas ─────────────────────────────────────────────────
    tts.speak("Jarvis online. Aguardando seus comandos, senhor.")

    # ── Loop principal ──────────────────────────────────────────────
    try:
        await audio.run()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        audio.is_listening = False
        print("\n[Main] Jarvis Worker encerrado.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Main] Interrompido pelo usuário.")
