"""
brain_dexter.py — Camada de tarefa pesada (Dexter via OpenClaw)

Chama o endpoint /v1/chat/completions do gateway OpenClaw com Dexter.
Dexter tem acesso completo a ferramentas, memória e contexto do sistema.

Função síncrona — rodar em ThreadPoolExecutor.
"""
import requests
import config

DEXTER_SYSTEM = """\
Resposta via voz. Seja DIRETO e CURTO.

- Máximo 2 frases. Nunca mais.
- Sem markdown, sem listas, sem asteriscos.
- Dados técnicos: simplifique. "3 servidores online" não "192.168.1.1, 192.168.1.2..."
- Responda em português.
- Se não souber ou não conseguir: diga em 1 frase.
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
