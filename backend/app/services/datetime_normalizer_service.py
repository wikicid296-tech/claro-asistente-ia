from __future__ import annotations
from typing import Optional, Dict
from datetime import datetime, timedelta
import json

from app.services.groq_service import run_groq_completion
from app.clients.groq_client import get_groq_client, get_groq_api_key

SYSTEM_PROMPT = """
Eres un normalizador de fecha y hora.
Devuelve SOLO un JSON válido.

Campos:
- fecha: YYYY-MM-DD o null
- hora: HH:MM o null

Reglas:
- Usa formato 24 horas
- Si el texto no contiene información suficiente, devuelve null
- NO inventes datos
"""

def normalize_datetime_from_text(
    *,
    text: str,
    now: Optional[datetime] = None
) -> Dict[str, Optional[str]]:

    now = now or datetime.now()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps({
                "text": text,
                "today": now.strftime("%Y-%m-%d"),
                "weekday": now.strftime("%A"),
            }, ensure_ascii=False)
        }
    ]

    raw = run_groq_completion(
        messages=messages,
        groq_client=get_groq_client(),
        groq_api_key=get_groq_api_key(),
        temperature=0.0,
        max_tokens=150,
    )

    try:
        data = json.loads(raw)
    except Exception:
        return {"fecha": None, "hora": None}

    fecha = data.get("fecha")
    hora = data.get("hora")

    return {
        "fecha": fecha if isinstance(fecha, str) else None,
        "hora": hora if isinstance(hora, str) else None,
    }
