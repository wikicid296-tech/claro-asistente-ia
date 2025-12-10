from __future__ import annotations

from typing import Any, Dict, Optional, Literal
import logging

from app.services.context_service import get_context_for_query
from app.services.prompt_service import build_urls_block, build_system_prompt
from app.services.channel_message_service import build_chat_messages
from app.services.groq_service import run_groq_completion

from app.clients.groq_client import get_groq_client, get_groq_api_key

logger = logging.getLogger(__name__)

Channel = Literal["web", "whatsapp", "sms", "rcs"]

DEFAULT_MODEL = "llama-3.3-70b-versatile"


# ------------------------------------------------------------
# LLM execution adapter
# ------------------------------------------------------------

def _run_llm(
    *,
    messages: list[dict[str, str]],
    groq_client=None,
    groq_api_key=None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.5,
    max_tokens: int = 2048,
) -> str:
    return run_groq_completion(
        messages=messages,
        groq_client=groq_client,
        groq_api_key=groq_api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


# ------------------------------------------------------------
# Orchestrators
# ------------------------------------------------------------

def run_web_chat(
    *,
    user_message: str,
    action: str = "busqueda",
    user_key: Optional[str] = None,
    groq_client: Any = None,
    groq_api_key: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 2048,
    model: str = DEFAULT_MODEL,
) -> Dict[str, Any]:
    """
    Orquestador para /chat (web).
    Compatible con firma usada en controllers.
    """

    if not user_message or not user_message.strip():
        raise ValueError("Mensaje vacío")

    # Resolver cliente/key si no se proporcionan
    if groq_client is None:
        groq_client = get_groq_client()
    if groq_api_key is None:
        groq_api_key = get_groq_api_key()

    # Contexto
    ctx = get_context_for_query(user_message)
    relevant_urls = ctx.get("relevant_urls", [])
    context_label = ctx.get("label", "ℹ️ Asistente general disponible")

    # Build URLs block
    urls_text = build_urls_block(relevant_urls)

    # Build prompt
    system_prompt = build_system_prompt("web", context_label, urls_text)

    # TODO: integrar memory_service real
    previous_messages: list[str] = []

    messages = build_chat_messages(
        system_prompt,
        user_message,
        previous_messages,
        max_prev=1
    )

    response_text = _run_llm(
        messages=messages,
        groq_client=groq_client,
        groq_api_key=groq_api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return {
        "success": True,
        "response": response_text,
        "context": context_label,
        "relevant_urls": relevant_urls[:5],
        "memory_used": len(previous_messages),
        "context_reset": len(previous_messages) == 0,
        "action": action,
    }


def run_channel_chat(
    *,
    channel: Channel,
    user_message: str,
    action: str = "busqueda",
    user_key: Optional[str] = None,
    groq_client: Any = None,
    groq_api_key: Optional[str] = None,
    temperature: float = 0.5,
    max_tokens: int = 500,
    model: str = DEFAULT_MODEL,
) -> Dict[str, Any]:
    """
    Orquestador unificado para WhatsApp, SMS y RCS.
    Firma compatible con controllers actuales.
    """

    if not user_message or not user_message.strip():
        raise ValueError("Mensaje vacío")

    if groq_client is None:
        groq_client = get_groq_client()
    if groq_api_key is None:
        groq_api_key = get_groq_api_key()

    ctx = get_context_for_query(user_message)
    relevant_urls = ctx.get("relevant_urls", [])
    context_label = ctx.get("label", "ℹ️ Asistente general disponible")

    # Build URLs block
    urls_text = build_urls_block(relevant_urls)

    # Build system prompt por canal
    system_prompt = build_system_prompt(channel, context_label, urls_text)

    # TODO: memory por canal
    previous_messages: list[str] = []

    # SMS no admite historial
    max_prev = 0 if channel == "sms" else 1

    messages = build_chat_messages(
        system_prompt,
        user_message,
        previous_messages,
        max_prev=max_prev
    )

    response_text = _run_llm(
        messages=messages,
        groq_client=groq_client,
        groq_api_key=groq_api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # Truncados por canal
    if channel == "sms":
        response_text = " ".join(response_text.split())
        if len(response_text) > 140:
            cutoff = response_text[:137].rfind(" ")
            response_text = (response_text[:cutoff] if cutoff > 0 else response_text[:137]) + "..."

    elif channel == "whatsapp" and len(response_text) > 1500:
        response_text = response_text[:1497] + "..."

    elif channel == "rcs" and len(response_text) > 1000:
        response_text = response_text[:997] + "..."

    return {
        "success": True,
        "response": response_text,
        "context": context_label,
        "relevant_urls": relevant_urls[:3],
        "memory_used": len(previous_messages),
        "context_reset": len(previous_messages) == 0,
        "action": action,
        "channel": channel,
    }
