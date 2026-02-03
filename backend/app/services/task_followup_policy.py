from __future__ import annotations
from typing import Dict, Optional

# Mapeo determinista: (task_kind, field) -> pregunta
FOLLOWUP_QUESTIONS = {
    ("meeting", "meeting_link"): "Perfecto, ¿ya cuentas con la liga del meeting?",
    ("meeting", "datetime"): "¿En qué fecha y hora será el evento?",
}


def decide_followup(analysis: Dict) -> Optional[Dict]:
    """
    Decide si se debe preguntar y qué preguntar.
    Devuelve None si no aplica.
    """
    task_kind = analysis.get("task_kind")
    if not isinstance(task_kind, str):
        return None

    missing_fields = analysis.get("missing_fields") or []
    if not isinstance(missing_fields, list):
        return None

    for field in missing_fields:
        if not isinstance(field, str):
            continue

        key: tuple[str, str] = (task_kind, field)
        question = FOLLOWUP_QUESTIONS.get(key)
        if question:
            return {
                "pending_field": field,
                "question": question,
            }

    return None
