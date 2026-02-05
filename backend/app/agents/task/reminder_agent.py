from __future__ import annotations

import json
import logging
from typing import Dict, Any

from app.services.datetime_normalizer_service import normalize_datetime_from_text
from app.services.groq_service import run_groq_completion
from app.clients.groq_client import get_groq_client, get_groq_api_key
from datetime import datetime
from zoneinfo import ZoneInfo

now = datetime.now(ZoneInfo("America/Mexico_City"))

now_iso = now.isoformat(timespec="minutes")
today = now.strftime("%Y-%m-%d")
weekday = now.strftime("%A")


logger = logging.getLogger(__name__)
SYSTEM_PROMPT = """
Eres un normalizador de recordatorios.

FECHA Y HORA ACTUAL (referencia absoluta):
- Fecha: {today}
- Fecha y hora ISO: {now_iso}
- Zona horaria: America/Mexico_City

Devuelve ÚNICAMENTE un JSON con:
- content: string
- fecha: YYYY-MM-DD | null
- hora: HH:MM | null
- lugar: string | "No especificado"

Reglas:
- Todas las fechas relativas ("mañana", "viernes", "en 2 horas")
  DEBEN resolverse usando ESTA referencia previa
- siempre devuelve fecha en formato YYYY-MM-DD o null si no se detecta
- content debe ser una acción corta en infinitivo, pero omitiendo la palabra instruccional inicial (ej. "Recordar", "No olvidar", "Agendar")
- NO incluir fecha, hora ni lugar en content
- Capitaliza nombres propios evidentes
- NO inventes datos
- Ejemplo de content valido esperado:
usuario: "recuerdame lavar el carro el viernes a las 3 de la tarde"
tu: "Lavar el carro"
ya que los demas detalles son capturados en los otros campos.

"""


def normalize_reminder(text: str) -> Dict[str, Any]:
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
    logger.info("✅✅✅✅✅✅ReminderAgent.normalize_reminder | raw=%r", raw)

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


class ReminderTaskAgent:
    def handle(
        self,
        *,
        content: str,
        analysis: Dict[str, Any],
        state: Any = None,
    ) -> Dict[str, Any]:

        dt = normalize_datetime_from_text(text=content)
        fecha = dt.get("fecha")
        hora = dt.get("hora")

        llm = normalize_reminder(content)

        content_final = llm.get("content", content)
        fecha = llm.get("fecha") or fecha
        hora = llm.get("hora") or hora
        lugar = llm.get("lugar")

        enrichment_candidates = []
        needs_followup = False

        if not fecha:
            needs_followup = True
            enrichment_candidates.append("fecha")

        if not hora:
            needs_followup = True
            enrichment_candidates.append("hora")
        
        import json

        logger.info(
            "ReminderAgent.handle | result=%s",
            json.dumps({
                "task_type": "reminder",
                "status": "created",
                "content": content_final,
                "fecha": fecha,
                "hora": hora,
                "lugar": lugar,
                "needs_followup": needs_followup,
                "enrichment_candidates": enrichment_candidates,
                "followup_question": None,
            }, ensure_ascii=False)
        )


        return {
            "task_type": "reminder",
            "status": "created",
            "content": content_final,
            "fecha": fecha,
            "hora": hora,
            "lugar": lugar,
            "needs_followup": needs_followup,
            "enrichment_candidates": enrichment_candidates,
            "followup_question": None,
        }
