from __future__ import annotations

import json
import logging
from typing import Dict, Any
from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.datetime_normalizer_service import normalize_datetime_from_text
from app.services.calendar_ics import crear_invitacion_ics
from app.services.groq_service import run_groq_completion
from app.clients.groq_client import get_groq_client, get_groq_api_key


logger = logging.getLogger(__name__)

now = datetime.now(ZoneInfo("America/Mexico_City"))
now_iso = now.isoformat(timespec="minutes")
today = now.strftime("%Y-%m-%d")


SYSTEM_PROMPT = f"""
Eres un normalizador de eventos de calendario.

FECHA Y HORA ACTUAL (referencia absoluta):
- Fecha: {today}
- Fecha y hora ISO: {now_iso}
- Zona horaria: America/Mexico_City

Devuelve ÚNICAMENTE un JSON con:
- titulo: string
- descripcion: string
- fecha: YYYY-MM-DD | null
- hora: HH:MM | null
- ubicacion: string | null

Reglas:
-Debes omitir en el titulo las palabras instruccionales como "Agendar", "Programar", "Crear evento"
- Todas las fechas relativas deben resolverse usando ESTA referencia
- titulo debe ser corto y limpio (sin fecha ni hora)
- descripcion puede ampliar el contexto
- NO inventes datos
- NO uses markdown
"""


def normalize_calendar_event(text: str) -> Dict[str, Any]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]

    raw = run_groq_completion(
        messages=messages,
        groq_client=get_groq_client(),
        groq_api_key=get_groq_api_key(),
        temperature=0.0,
        max_tokens=250,
    )

    logger.info("📅 CalendarAgent.normalize_calendar_event | raw=%r", raw)

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


class CalendarTaskAgent:
    def handle(
        self,
        *,
        content: str,
        analysis: Dict[str, Any],
        state: Any = None,
    ) -> Dict[str, Any]:

        missing = set(analysis.get("missing_fields", []) or [])

        needs_meeting_link = "meeting_link" in missing

        dt = normalize_datetime_from_text(text=content)
        fecha = dt.get("fecha")
        hora = dt.get("hora")

        needs_datetime = not (fecha and hora)

        enrichment_candidates = []
        if needs_meeting_link:
            enrichment_candidates.append("meeting_link")
        if needs_datetime:
            enrichment_candidates.append("datetime")

        llm = normalize_calendar_event(content)

        titulo = llm.get("titulo", content)
        descripcion = llm.get("descripcion", titulo)
        ubicacion = llm.get("ubicacion")

        fecha = llm.get("fecha") or fecha
        hora = llm.get("hora") or hora

        ics = None
        if fecha and hora:
            ics = crear_invitacion_ics(
                titulo=titulo,
                descripcion=descripcion,
                fecha=fecha,
                hora=hora,
            )

        logger.info(
            "CalendarAgent.handle | result=%s",
            json.dumps({
                "task_type": "calendar",
                "content": titulo,
                "fecha": fecha,
                "hora": hora,
                "ubicacion": ubicacion,
                "needs_followup": bool(enrichment_candidates),
                "enrichment_candidates": enrichment_candidates,
            }, ensure_ascii=False)
        )

        return {
            "task_type": "calendar",
            "status": "created",
            "content": titulo,
            "fecha": fecha,
            "hora": hora,
            "ubicacion": ubicacion,
            "ics": ics,
            "enrichment_candidates": enrichment_candidates,
            "needs_followup": bool(enrichment_candidates),
            "followup_question": None,
        }
