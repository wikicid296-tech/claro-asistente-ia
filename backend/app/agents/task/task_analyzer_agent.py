from __future__ import annotations

import json
from typing import Dict, Any

from app.services.groq_service import run_groq_completion
from app.clients.groq_client import get_groq_client, get_groq_api_key


SYSTEM_PROMPT = """
Eres un analizador de tareas.
NO escribas mensajes para el usuario.
NO inventes información.
NO hagas preguntas.

Tu tarea es analizar el texto y devolver ÚNICAMENTE un JSON válido con:
- task_kind: meeting | reminder | note | unknown
- has_datetime: true | false
- has_participants: true | false
- has_meeting_link: true | false
- missing_fields: array de strings

Reglas:
- Si el texto menciona videollamada, reunión, junta, call → task_kind = meeting
- Un meeting puede existir sin liga.
- Si no estás seguro, marca false.
- Nunca incluyas texto fuera del JSON.
"""


def analyze_task(
    *,
    text: str,
    task_type: str,
) -> Dict[str, Any]:

    client = get_groq_client()
    api_key = get_groq_api_key()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps({
                "task_type": task_type,
                "text": text
            }, ensure_ascii=False)
        }
    ]

    raw = run_groq_completion(
        messages=messages,
        groq_client=client,
        groq_api_key=api_key,
        temperature=0.0,
        max_tokens=300,
    )

    try:
        data = json.loads(raw)
    except Exception:
        # Fallback ultra seguro
        data = {
            "task_kind": "unknown",
            "has_datetime": False,
            "has_participants": False,
            "has_meeting_link": False,
            "missing_fields": []
        }

    return data
