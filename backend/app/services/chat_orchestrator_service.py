from __future__ import annotations

from typing import Any, Dict, Optional, Literal
import logging
import re

from app.services.context_service import get_context_for_query
from app.services.prompt_service import build_urls_block, build_system_prompt
from app.services.channel_message_service import build_chat_messages
from app.services.groq_service import run_groq_completion

from app.clients.groq_client import get_groq_client, get_groq_api_key

logger = logging.getLogger(__name__)

Channel = Literal["web", "whatsapp", "sms", "rcs"]

DEFAULT_MODEL = "llama-3.3-70b-versatile"


# ------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------

def extract_course_id_from_query(text: str):
    if not text:
        return None

    patterns = [
        r'\bcurso\s*(?:no\.?|número|numero|#)?\s*(\d+)\b',
        r'\bno\.?\s*(\d+)\b',
        r'\b#(\d+)\b',
        r'\b(\d{1,4})\b'
    ]

    text = text.lower()
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1)

    return None


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
    messages: list[dict],
    action: str = "busqueda",
    groq_client: Any = None,
    groq_api_key: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 2048,
    model: str = DEFAULT_MODEL,
) -> Dict[str, Any]:
    """
    Orquestador LLM puro.
    NO maneja memoria. Recibe mensajes ya construidos.
    """

    if not messages:
        raise ValueError("Lista de mensajes vacía")

    # Resolver cliente/key si no se proporcionan
    if groq_client is None:
        groq_client = get_groq_client()
    if groq_api_key is None:
        groq_api_key = get_groq_api_key()

    # Último mensaje del usuario (solo para heurísticas)
    user_message = messages[-1]["content"]

    # Contexto informativo
    ctx = get_context_for_query(user_message)
    relevant_urls = ctx.get("relevant_urls", [])
    context_label = ctx.get("label", "ℹ️ Asistente general disponible")

    urls_text = build_urls_block(relevant_urls)
    system_prompt = build_system_prompt("web", context_label, urls_text)

    # Inyectar system prompt al inicio
    final_messages = [{"role": "system", "content": system_prompt}] + messages

    # Heurística de tareas
    is_task_request = any(keyword in user_message.lower() for keyword in [
        'recuerdame', 'recuérdame', 'recordar', 'agenda', 'agendar',
        'nota', 'anota', 'guardar', 'junta', 'reunión', 'cita'
    ])

    final_temperature = 0.1 if is_task_request else temperature
    final_max_tokens = 512 if is_task_request else max_tokens

    response_text = _run_llm(
        messages=final_messages,
        groq_client=groq_client,
        groq_api_key=groq_api_key,
        model=model,
        temperature=final_temperature,
        max_tokens=final_max_tokens,
    )

    return {
        "success": True,
        "response": response_text,
        "context": context_label,
        "relevant_urls": relevant_urls[:5],
        "memory_used": len(messages) - 1,
        "context_reset": False,
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
    NO maneja memoria conversacional.
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

    urls_text = build_urls_block(relevant_urls)

    system_prompt = build_system_prompt(channel, context_label, urls_text)

    # Canales no soportan historial largo
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    response_text = _run_llm(
        messages=messages,
        groq_client=groq_client,
        groq_api_key=groq_api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # Truncado por canal
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
        "memory_used": 0,
        "context_reset": True,
        "action": action,
        "channel": channel,
    }
