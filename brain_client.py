"""
brain_client.py — Cliente HTTP para o OpenClaw /v1/chat/completions

Função síncrona (usada em ThreadPoolExecutor pelo TaskManager).
"""
import requests
import config


VOICE_SYSTEM_PROMPT = """\
Você está em modo de interface de voz. O usuário falou por microfone e \
ouvirá sua resposta em áudio via síntese de voz (ElevenLabs TTS).

Regras para resposta em voz:
- Responda de forma CONCISA e natural para fala (máximo 2-3 frases curtas)
- SEM markdown, SEM asteriscos, SEM listas com traço ou número
- SEM emojis (não funcionam em áudio)
- Fale naturalmente como em uma conversa, não como texto escrito
- Se precisar enumerar, use "primeiro... segundo... terceiro..."
- Evite URLs, códigos, e formatação que soe estranha quando falada
"""


def ask_brain(text: str) -> str:
    """Envia comando ao OpenClaw e retorna a resposta do LLM como string.
    
    Inclui system prompt de contexto de voz para que o LLM responda
    de forma adequada para síntese de voz (sem markdown, conciso).
    """
    headers = {
        "Authorization": f"Bearer {config.GATEWAY_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "openclaw",
        "user": config.WORKER_ID,
        "stream": False,
        "messages": [
            {"role": "system", "content": VOICE_SYSTEM_PROMPT},
            {"role": "user", "content": text},
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
