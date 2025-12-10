from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import requests

from app.services.usage_service import calculate_cost, add_usage

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama-3.3-70b-versatile"


# -------------------------------------------------------------------
# Tracking helpers
# -------------------------------------------------------------------

def track_groq_usage_from_sdk(usage_obj: Any) -> None:
    """
    Extrae prompt_tokens y completion_tokens desde un objeto usage del SDK.
    """
    if not usage_obj:
        return

    try:
        input_tokens = int(getattr(usage_obj, "prompt_tokens", 0) or 0)
        output_tokens = int(getattr(usage_obj, "completion_tokens", 0) or 0)

        if input_tokens or output_tokens:
            cost = calculate_cost(input_tokens, output_tokens, "groq")
            add_usage(cost)

    except Exception as e:
        logger.error(f"Error trackeando tokens Groq SDK: {e}")


def track_groq_usage_from_http(result: Dict[str, Any]) -> None:
    """
    Extrae prompt_tokens y completion_tokens desde respuesta HTTP.
    """
    try:
        usage = (result or {}).get("usage") or {}
        input_tokens = int(usage.get("prompt_tokens", 0) or 0)
        output_tokens = int(usage.get("completion_tokens", 0) or 0)

        if input_tokens or output_tokens:
            cost = calculate_cost(input_tokens, output_tokens, "groq")
            add_usage(cost)

    except Exception as e:
        logger.error(f"Error trackeando tokens Groq HTTP: {e}")


# -------------------------------------------------------------------
# HTTP Fallback
# -------------------------------------------------------------------

def call_groq_api_directly(
    *,
    messages: List[Dict[str, str]],
    api_key: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.5,
    max_tokens: int = 2048,
    top_p: Optional[float] = None,
    frequency_penalty: Optional[float] = None,
    timeout_seconds: int = 30
) -> Dict[str, Any]:
    """
    Llamada directa al endpoint OpenAI-compatible de Groq.
    """
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if top_p is not None:
        payload["top_p"] = top_p
    if frequency_penalty is not None:
        payload["frequency_penalty"] = frequency_penalty

    response = requests.post(url, headers=headers, json=payload, timeout=timeout_seconds)
    response.raise_for_status()
    return response.json()


def call_groq_api_directly_sms(
    *,
    messages: List[Dict[str, str]],
    api_key: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.3,
    max_tokens: int = 40,
    top_p: float = 0.9,
    frequency_penalty: float = 0.5,
    timeout_seconds: int = 30
) -> Dict[str, Any]:
    """
    Variante especial para SMS con límites estrictos.
    """
    return call_groq_api_directly(
        messages=messages,
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        timeout_seconds=timeout_seconds
    )


# -------------------------------------------------------------------
# Unified chat execution
# -------------------------------------------------------------------

def run_groq_completion(
    *,
    messages: List[Dict[str, str]],
    groq_client: Any = None,
    groq_api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.5,
    max_tokens: int = 2048,
    top_p: Optional[float] = None,
    frequency_penalty: Optional[float] = None
) -> str:
    """
    Ejecuta una completion usando:
      1) SDK si está disponible y no es 'api_fallback'
      2) HTTP fallback si hay API key

    Retorna el texto final de respuesta.
    """
    # 1) Preferencia: SDK
    if groq_client and groq_client != "api_fallback":
        completion = groq_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p if top_p is not None else 1,
            frequency_penalty=frequency_penalty if frequency_penalty is not None else 0
        )
        text = completion.choices[0].message.content

        try:
            track_groq_usage_from_sdk(getattr(completion, "usage", None))
        except Exception:
            pass

        return text

    # 2) Fallback: HTTP directo
    if not groq_api_key:
        raise RuntimeError("GROQ_API_KEY requerida para fallback HTTP")

    result = call_groq_api_directly(
        messages=messages,
        api_key=groq_api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        frequency_penalty=frequency_penalty
    )
    text = result["choices"][0]["message"]["content"]

    try:
        track_groq_usage_from_http(result)
    except Exception:
        pass

    return text
