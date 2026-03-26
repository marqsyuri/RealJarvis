"""
brain_client.py — Cliente HTTP para o OpenClaw /v1/chat/completions

Função síncrona (usada em ThreadPoolExecutor pelo TaskManager).
"""
import requests
import config


def ask_brain(text: str) -> str:
    """Envia comando ao OpenClaw e retorna a resposta do LLM como string.
    
    Lança requests.HTTPError em caso de erro HTTP.
    Lança requests.Timeout se BRAIN_TIMEOUT for excedido.
    """
    headers = {
        "Authorization": f"Bearer {config.GATEWAY_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "openclaw",
        "user": config.WORKER_ID,
        "stream": False,
        "messages": [{"role": "user", "content": text}],
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
