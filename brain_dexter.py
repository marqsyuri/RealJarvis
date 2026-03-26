"""
brain_dexter.py — Camada de tarefa pesada (Dexter via OpenClaw)

Chama o endpoint /v1/chat/completions do gateway OpenClaw com Dexter.
Dexter tem acesso completo a ferramentas, memória e contexto do sistema.

Função síncrona — rodar em ThreadPoolExecutor.
"""
import requests
import config

DEXTER_SYSTEM = """\
Você está recebendo uma tarefa via interface de voz do JARVIS Worker.
O usuário ouvirá sua resposta falada via ElevenLabs TTS.

Regras para resposta por voz:
- Seja conciso: máximo 3 frases
- Sem markdown, sem asteriscos, sem listas formatadas
- Se precisar enumerar: "primeiro... segundo... terceiro..."
- Responda em português
- Se a tarefa envolver dados técnicos (IPs, códigos), simplifique para fala
"""


def ask_dexter(task: str) -> str:
    """Envia tarefa ao Dexter via OpenClaw e retorna resposta como string."""
    headers = {
        "Authorization": f"Bearer {config.GATEWAY_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "openclaw",
        "user": config.WORKER_ID,
        "stream": False,
        "messages": [
            {"role": "system", "content": DEXTER_SYSTEM},
            {"role": "user", "content": task},
        ],
    }
    resp = requests.post(
        f"{config.GATEWAY_HTTP}/v1/chat/completions",
        json=payload,
        headers=headers,
        timeout=config.BRAIN_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]
