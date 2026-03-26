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
# Vozes disponíveis no plano free (testadas em PT-BR):
#   Brian            → nPczCjzI2devNBz1zQrb  (Deep, Resonant) ← padrão JARVIS PT
#   Menina Naturalista→ VzMPkbfceYEaZTe52axN  (única voz PT nativa — feminina)
#   Callum           → N2lVS1w4EtoT3dr4eOWO  (Husky, mais frio)
#   George           → JBFqnCBsd6RMkjVDRZzb  (Warm, Storyteller)
# Nota: vozes da Voice Library (comunidade) exigem plano pago
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "nPczCjzI2devNBz1zQrb")
ELEVENLABS_MODEL    = "eleven_multilingual_v2"  # multilingual → fala PT-BR sem sotaque
# Alternativa mais rápida (200ms menos): "eleven_turbo_v2_5" (ligeiramente pior em PT)
# PCM removido — usa MP3 direto via pygame (sem problema de sample rate no Windows)

# ═══════════════════════════════════════════════════════════
#  Anthropic — Haiku (camada de voz rápida)
# ═══════════════════════════════════════════════════════════
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

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
LISTEN_TIMEOUT = 1    # segundos (modo wake word — loop curto pra detectar rápido)
PHRASE_LIMIT   = 6    # reduzido: comandos de voz são curtos (< 6s normalmente)

# Modo conversa
CONVERSATION_SILENCE_TIMEOUTS = 3   # 3 × timeout = ~3s silêncio → sai do modo conversa
CONVERSATION_EXIT_PHRASES = {
    "pode ir", "dispensado", "obrigado", "obrigada",
    "tchau", "até logo", "até mais", "encerra", "encerrar",
    "sair", "pare", "parar",
}

# ═══════════════════════════════════════════════════════════
#  Task Manager
# ═══════════════════════════════════════════════════════════
MAX_BRAIN_WORKERS = 3   # requisições paralelas ao LLM
BRAIN_TIMEOUT     = 90  # timeout de cada requisição HTTP (segundos)
