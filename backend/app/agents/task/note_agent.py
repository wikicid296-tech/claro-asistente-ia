from __future__ import annotations
from typing import Dict, Any


class NoteAgent:
    """
    Agente de notas.
    - No hace preguntas
    - No maneja fechas
    - Prepara contenido limpio y opcionalmente resumen
    """

    def handle(
        self,
        *,
        content: str,
        analysis: Dict[str, Any],
        state: Any = None,
    ) -> Dict[str, Any]:

        # En notas, el análisis casi siempre es trivial
        title = content[:60].strip()

        return {
            "task_type": "note",
            "status": "created",
            "title": title,
            "content": content,
            "needs_followup": False,
            "followup_question": None,
        }
