from textwrap import dedent
import json
import logging
import re

logger = logging.getLogger(__name__)


class _SafeDict(dict):
    def __missing__(self, key):
        # Cada vez que falte algo, devuelve string vacío en vez de lanzar KeyError
        return ""


def build_urls_block(urls):
    if urls is None:
        return ""
    if isinstance(urls, str):
        return urls
    try:
        return json.dumps(urls, ensure_ascii=False, indent=2)
    except Exception:
        return str(urls)


def build_system_prompt(channel: str, context: str = "", urls_text: str = "") -> str:
    """
    Construye el prompt SYSTEM aplicando formateo seguro.
    """
    from app.prompts import (
        SYSTEM_PROMPT,
        WHATSAPP_SYSTEM_PROMPT,
        SMS_SYSTEM_PROMPT,
        RCS_SYSTEM_PROMPT,
    )

    # Elegimos prompt según canal:
    if channel == "whatsapp":
        template = WHATSAPP_SYSTEM_PROMPT
    elif channel == "sms":
        template = SMS_SYSTEM_PROMPT
    elif channel == "rcs":
        template = RCS_SYSTEM_PROMPT
    else:
        template = SYSTEM_PROMPT  # canal web/default

    mapping = _SafeDict({
        "context": context or "",
        "urls": urls_text or "",
    })

    try:
        return template.format_map(mapping)
    except Exception as e:
        logger.error(f"[build_system_prompt] Error formateando template: {e}")
        logger.error(f"Template problematico:\n{template}")
        logger.error(f"Mapping usado: {mapping}")
        # Devolvemos template sin formatear para evitar 500
        return template

def is_aprende_intent(user_message: str, action: str = "") -> bool:
    t = (user_message or "").lower()
    a = (action or "").lower()

    # 🔥 PRIORIDAD ABSOLUTA: modo forzado desde frontend
    if a == "aprende":
        return True

    # Heurística lingüística
    patterns = [
        r"\baprende\b",
    ]

    return any(re.search(p, t) for p in patterns)

def is_telcel_intent(user_message: str, action: str = "") -> bool:
    t = (user_message or "").lower()
    a = (action or "").lower()

    if a == "telcel":
        return True

    patterns = [
        r"\btelcel\b"
    ]

    return any(re.search(p, t) for p in patterns)

def is_claro_intent(user_message: str, action: str = "") -> bool:
    t = (user_message or "").lower()
    a = (action or "").lower()

    if a == "claro":
        return True

    patterns = [
        r"\bclaro\b"
    ]

    return any(re.search(p, t) for p in patterns)
