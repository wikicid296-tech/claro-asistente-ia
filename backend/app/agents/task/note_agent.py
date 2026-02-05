from __future__ import annotations

import json
import logging
from typing import Dict, Any

from app.services.groq_service import run_groq_completion
from app.clients.groq_client import get_groq_client, get_groq_api_key


logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
Eres un normalizador de notas.

Devuelve ÚNICAMENTE un JSON con:
- title: string
- content: string

Reglas:
-Debes omitir en el titulo las palabras instruccionales como "Agendar", "Programar", "Crear evento"
- title debe ser corto, claro y descriptivo
- content debe mantener el significado original
- NO inventes información
- NO uses markdown
"""


def normalize_note(text: str) -> Dict[str, Any]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]

    raw = run_groq_completion(
        messages=messages,
        groq_client=get_groq_client(),
        groq_api_key=get_groq_api_key(),
        temperature=0.0,
        max_tokens=200,
    )

    logger.info("📝 NoteAgent.normalize_note | raw=%r", raw)

    if not raw or not raw.strip():
        return {}

    cleaned = raw.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        lines = cleaned.splitlines()
        if lines and lines[0].strip().lower() == "json":
            cleaned = "\n".join(lines[1:]).strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    return {}


class NoteAgent:
    def handle(
        self,
        *,
        content: str,
        analysis: Dict[str, Any],
        state: Any = None,
    ) -> Dict[str, Any]:

        llm = normalize_note(content)

        title = llm.get("title", content[:60].strip())
        body = llm.get("content", content)

        logger.info(
            "NoteAgent.handle | result=%s",
            json.dumps({
                "task_type": "note",
                "title": title,
                "content": body,
            }, ensure_ascii=False)
        )

        return {
            "task_type": "note",
            "status": "created",
            "title": title,
            "content": body,
            "needs_followup": False,
            "followup_question": None,
        }
