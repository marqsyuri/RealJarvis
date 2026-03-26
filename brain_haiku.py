"""
brain_haiku.py — Camada de voz rápida (Claude Haiku)

Fluxo:
  1. Recebe comando de voz
  2. Chama Haiku (~400ms) com contexto de voz e ferramenta dexter_task
  3. Retorna HaikuResult:
     - immediate_response: o que falar AGORA (sempre presente)
     - dexter_task: tarefa a enviar pro Dexter em background (ou None)

Haiku decide sozinho: resposta direta OU delega pro Dexter.
Exemplos:
  "que horas são?" → resposta direta, sem Dexter
  "status dos servidores?" → "Verificando agora..." + dexter_task
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

import anthropic
import config

# ── Configuração ─────────────────────────────────────────────────────

HAIKU_MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 400

JARVIS_SYSTEM = """\
Você é JARVIS, assistente de voz do Yuri. Fale português. Seja CURTÍSSIMO.

REGRA PRINCIPAL: máximo 1 frase. Nunca mais que isso.
- Sem explicações. Sem contexto. Só a resposta.
- Sem markdown, listas, asteriscos, emojis.
- Resposta de voz = fala humana natural, direta.

EXEMPLOS CORRETOS:
  Pergunta: "tá por aí?"       → "Tô sim, pode falar."
  Pergunta: "que horas são?"   → "São quase meia-noite."
  Pergunta: "como você tá?"    → "Tudo certo por aqui."

EXEMPLOS ERRADOS (nunca faça):
  "Olá Yuri! Estou aqui e pronto para ajudá-lo no que precisar..."
  "Claro! Posso fazer isso por você. Primeiro vou verificar..."

USE dexter_task APENAS para ações reais no sistema:
- Status de servidores ou apps
- Executar comandos, verificar logs
- Pesquisas em tempo real

Para tudo mais (conversa, perguntas gerais): responda direto, 1 frase.
"""

DEXTER_TASK_TOOL = {
    "name": "dexter_task",
    "description": (
        "Delega uma tarefa complexa ao Dexter — IA com acesso completo a "
        "ferramentas, servidores Conceitto, código e internet. "
        "Use para tudo que exige ação real no sistema."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "immediate_response": {
                "type": "string",
                "description": (
                    "O que falar ao usuário AGORA enquanto Dexter processa. "
                    "Ex: 'Verificando os servidores.' / 'Analisando o erro.'"
                ),
            },
            "task": {
                "type": "string",
                "description": "Instrução completa para o Dexter executar.",
            },
        },
        "required": ["immediate_response", "task"],
    },
}


# ── Resultado tipado ──────────────────────────────────────────────────

@dataclass
class HaikuResult:
    immediate_response: str         # falar agora
    dexter_task: Optional[str] = None  # tarefa background (None = sem Dexter)


# ── Cliente ───────────────────────────────────────────────────────────

_client: Optional[anthropic.Anthropic] = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def ask_haiku(text: str) -> HaikuResult:
    """Chama Haiku e retorna resposta imediata + tarefa opcional pro Dexter.
    
    Função síncrona — rodar em ThreadPoolExecutor.
    """
    client = _get_client()

    response = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=MAX_TOKENS,
        system=JARVIS_SYSTEM,
        tools=[DEXTER_TASK_TOOL],
        messages=[{"role": "user", "content": text}],
    )

    # ── Processar resposta ────────────────────────────────────────────
    immediate = ""
    dexter_task = None

    for block in response.content:
        if block.type == "text":
            immediate += block.text.strip()
        elif block.type == "tool_use" and block.name == "dexter_task":
            inp = block.input
            immediate = inp.get("immediate_response", "Verificando...")
            dexter_task = inp.get("task")

    if not immediate:
        immediate = "Entendido."

    return HaikuResult(immediate_response=immediate, dexter_task=dexter_task)
