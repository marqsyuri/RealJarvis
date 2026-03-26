"""
config.py — Configurações centralizadas do Jarvis Worker
Edite aqui ou defina via variáveis de ambiente / arquivo .env
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv opcional

# ═══════════════════════════════════════════════════════════
#  ElevenLabs TTS
# ═══════════════════════════════════════════════════════════
ELEVENLABS_API_KEY  = os.getenv("ELEVENLABS_API_KEY", "")
# Troque ELEVENLABS_VOICE_ID pelo voice_id da voz JARVIS encontrada na
# voice library: https://elevenlabs.io/app/voice-library
# Voz padrão: "Adam" (grave, autoritativo americano)
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")
ELEVENLABS_MODEL    = "eleven_turbo_v2_5"   # ~100ms latência | alternativa: eleven_flash_v2_5
ELEVENLABS_SAMPLE_RATE    = 24000
ELEVENLABS_OUTPUT_FORMAT  = "pcm_24000"     # raw PCM, sem decode de MP3

# ═══════════════════════════════════════════════════════════
#  OpenClaw Gateway
# ═══════════════════════════════════════════════════════════
GATEWAY_HTTP  = "http://191.252.109.18:18789"
GATEWAY_WS    = "ws://191.252.109.18:18789"
GATEWAY_TOKEN = "fc120b7b67a5d8c148e1429d88699e2e51ca80a67ff82af6d9754d5a8e1d4ffb"
WORKER_ID     = "LENOVO_YURI"

# ═══════════════════════════════════════════════════════════
#  Reconhecimento de voz
# ═══════════════════════════════════════════════════════════
WAKE_WORD      = "jarvis"
STT_LANGUAGE   = "pt-BR"
LISTEN_TIMEOUT = 1    # segundos de silêncio → WaitTimeoutError (mantém loop vivo)
PHRASE_LIMIT   = 12   # duração máxima de uma fala em segundos

# ═══════════════════════════════════════════════════════════
#  Task Manager
# ═══════════════════════════════════════════════════════════
MAX_BRAIN_WORKERS = 3   # requisições paralelas ao LLM
BRAIN_TIMEOUT     = 90  # timeout de cada requisição HTTP (segundos)
