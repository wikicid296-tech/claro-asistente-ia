from __future__ import annotations
from typing import Dict, Any

from app.services.datetime_normalizer_service import normalize_datetime_from_text


class ReminderTaskAgent:
    """
    Agente de recordatorios.

    Responsabilidad:
    - Interpretar intención
    - Extraer fecha y hora (si existen)
    - Indicar si falta información

    NO debe:
    - Generar ICS
    - Ejecutar efectos
    """

    def handle(
        self,
        *,
        content: str,
        analysis: Dict[str, Any],
        state: Any = None,
    ) -> Dict[str, Any]:

        # -----------------------------
        # Normalización fecha / hora
        # -----------------------------
        dt = normalize_datetime_from_text(text=content)

        fecha = dt.get("fecha")
        hora = dt.get("hora")

        # -----------------------------
        # Decidir follow-up
        # -----------------------------
        needs_followup = False
        enrichment_candidates: list[str] = []

        if not fecha:
            needs_followup = True
            enrichment_candidates.append("fecha")

        if not hora:
            needs_followup = True
            enrichment_candidates.append("hora")

        return {
            "task_type": "reminder",
            "status": "created",
            "content": content,

            # Datos interpretados
            "fecha": fecha,
            "hora": hora,

            # Follow-up
            "needs_followup": needs_followup,
            "enrichment_candidates": enrichment_candidates,
            "followup_question": None,
        }
