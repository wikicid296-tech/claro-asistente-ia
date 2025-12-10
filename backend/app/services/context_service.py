# backend/app/services/context_service.py
from __future__ import annotations

from typing import Optional, List, Dict, Any
import logging

from app.prompts import URLS

logger = logging.getLogger(__name__)


def detect_country(text: str) -> Optional[str]:
    text_lower = (text or "").lower()
    country_keywords = {
        "mexico": ["mexico", "méxico", "cdmx"],
        "argentina": ["argentina", "buenos aires"],
        "peru": ["peru", "perú", "lima"],
        "chile": ["chile", "santiago"],
        "austria": ["austria", "viena"],
        "bulgaria": ["bulgaria", "sofia"],
        "croacia": ["croacia", "zagreb"],
        "bielorrusia": ["bielorrusia", "belarus", "minsk"],
        "serbia": ["serbia", "belgrado"],
        "eslovenia": ["eslovenia", "liubliana"],
        "macedonia": ["macedonia", "skopje"],
    }

    for country, keywords in country_keywords.items():
        if any(k in text_lower for k in keywords):
            return country
    return None


def detect_operator(text: str) -> Optional[str]:
    text_lower = (text or "").lower()
    if "claro" in text_lower:
        return "claro"
    if "telcel" in text_lower:
        return "telcel"
    if "a1" in text_lower or "a one" in text_lower:
        return "a1"
    return None


def detect_topic(text: str) -> Optional[str]:
    text_lower = (text or "").lower()

    health_words = ["salud", "medico", "médico", "hospital", "doctor", "enfermedad", "tratamiento"]
    education_words = ["educacion", "educación", "curso", "aprender", "estudiar", "clase", "capacitacion", "capacitación"]

    if any(w in text_lower for w in health_words):
        return "health"
    if any(w in text_lower for w in education_words):
        return "education"
    return None


def get_relevant_urls(prompt: str) -> List[str]:
    """
    Replica limpia de la lógica original en tu services.py,
    eliminando prints y errores de tipado.
    """
    country = detect_country(prompt)
    operator = detect_operator(prompt)
    topic = detect_topic(prompt)

    selected: List[str] = []

    # Prioridad 1: Salud o Educación
    if topic and topic in URLS:
        topic_urls = URLS.get(topic, [])
        if isinstance(topic_urls, list):
            selected.extend(topic_urls[:2])

    # Prioridad 2: Telecom
    elif operator == "telcel" or country == "mexico":
        telcel_urls = URLS.get("telcel", [])
        if isinstance(telcel_urls, list):
            selected.extend(telcel_urls)

    elif operator == "claro":
        claro_block = URLS.get("claro", {})
        if isinstance(claro_block, dict) and country and country in claro_block:
            selected.extend(claro_block[country][:2])

    elif operator == "a1":
        a1_block = URLS.get("a1", {})
        if isinstance(a1_block, dict) and country and country in a1_block:
            selected.extend(a1_block[country][:1])

    # Fallback
    if not selected:
        telcel_urls = URLS.get("telcel", [])
        if isinstance(telcel_urls, list):
            selected.extend(telcel_urls)

    # Dedup preservando orden
    return list(dict.fromkeys(selected))


def _build_context_label(topic: Optional[str], operator: Optional[str], country: Optional[str]) -> str:
    if topic == "education":
        return "🎓 Educación y cursos"
    if topic == "health":
        return "🩺 Salud y bienestar"

    if operator == "telcel" or country == "mexico":
        return "📶 Telecom (Telcel/México)"
    if operator == "claro":
        return "📶 Telecom (Claro)"
    if operator == "a1":
        return "📶 Telecom (A1)"

    return "ℹ️ Asistente general disponible"


def get_context_for_query(prompt: str) -> Dict[str, Any]:
    """
    Contrato esperado por chat_orchestrator_service:
    {
      "label": str,
      "relevant_urls": list[str]
    }
    """
    country = detect_country(prompt)
    operator = detect_operator(prompt)
    topic = detect_topic(prompt)

    relevant_urls = get_relevant_urls(prompt)
    label = _build_context_label(topic, operator, country)

    return {
        "label": label,
        "relevant_urls": relevant_urls,
        "country": country,
        "operator": operator,
        "topic": topic,
    }
