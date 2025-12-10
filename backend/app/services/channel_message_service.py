# backend/app/services/channel_message_service.py
from __future__ import annotations

from typing import List, Dict, Any, Optional


def build_chat_messages(
    system_prompt: str,
    user_message: str,
    previous_messages: Optional[List[str]] = None,
    max_prev: int = 1,
) -> List[Dict[str, str]]:
    """
    Construye lista de mensajes para un chat LLM.
    Mantiene historial corto para no inflar tokens.
    """
    msgs: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

    prev = previous_messages or []
    if max_prev > 0 and prev:
        for pm in prev[-max_prev:]:
            if pm and pm.strip() and pm.strip() != user_message.strip():
                msgs.append({"role": "user", "content": pm})

    msgs.append({"role": "user", "content": user_message})
    return msgs
