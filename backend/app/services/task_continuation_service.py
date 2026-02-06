from __future__ import annotations
from typing import Dict, Any
import logging
import re

from app.services.task_calendar_service import generate_ics_for_task
from app.services.task_content_synthesizer import synthesize_task_content
from app.stores.task_store import add_task, get_tasks_grouped
from app.domain.task import Task

logger = logging.getLogger(__name__)

_DATE_HINT_RE = re.compile(
    r"(\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?\b|"
    r"\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\b|"
    r"\b(lunes|martes|mi[eé]rcoles|jueves|viernes|s[áa]bado|domingo)\b|"
    r"\b(hoy|ma[nñ]ana|pasado ma[nñ]ana)\b)",
    re.IGNORECASE,
)

_TIME_HINT_RE = re.compile(
    r"\b(?:a\s*las\s*)?(\d{1,2})(?::(\d{2}))?\s*"
    r"(am|pm|a\.m\.|p\.m\.|de la mañana|de la tarde|de la noche)?\b",
    re.IGNORECASE,
)


def _has_explicit_date(text: str) -> bool:
    return bool(_DATE_HINT_RE.search(text or ""))

def _extract_time_from_text(text: str) -> str | None:
    match = _TIME_HINT_RE.search(text or "")
    if not match:
        return None

    hour_str, minute_str, suffix = match.groups()
    try:
        hour = int(hour_str)
        minute = int(minute_str) if minute_str is not None else 0
    except ValueError:
        return None

    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None

    suffix_norm = (suffix or "").lower().strip()
    has_suffix = bool(suffix_norm)

    if has_suffix:
        if suffix_norm in ("pm", "p.m.", "de la tarde", "de la noche"):
            if hour < 12:
                hour += 12
            if suffix_norm == "de la noche" and hour == 12:
                hour = 0
        elif suffix_norm in ("am", "a.m.", "de la mañana"):
            if hour == 12:
                hour = 0
    else:
        # Sin sufijo: aceptar solo formato 24h o con minutos explícitos
        if hour < 13 and minute_str is None:
            return None

    return f"{hour:02d}:{minute:02d}"


def handle_task_continuation(
    *,
    user_message: str,
    pending_field: str,
    task_snapshot: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Consume la respuesta del usuario para enriquecer la tarea.
    Maneja explícitamente la transición entre slots (meeting_link -> datetime -> completed).
    """
    updated_task = dict(task_snapshot)
    if updated_task.get("location") is None and updated_task.get("ubicacion"):
        updated_task["location"] = updated_task.get("ubicacion")
    user_msg_lower = user_message.lower()

    # -------------------------------------------------
    # SLOT: meeting_link
    # -------------------------------------------------
    if pending_field == "meeting_link":
        has_datetime = bool(updated_task.get("fecha") and updated_task.get("hora"))
        presencial_keywords = [
            "presencial", "en persona", "en oficina", "físico", "fisico",
            "cara a cara",
        ]
        negative_link_keywords = [
            "no necesito link", "no necesito liga", "no hace falta link",
            "no hace falta liga", "sin link", "sin liga", "no hay link",
            "no hay liga", "no tengo link", "no tengo liga",
        ]

        # Caso: usuario indica que es presencial / sin liga
        if any(keyword in user_msg_lower for keyword in presencial_keywords):
            updated_task["meeting_link"] = None
            updated_task["meeting_type"] = "presencial"
            if has_datetime:
                updated_task["status"] = "completed"
                updated_task.pop("next_slot", None)
                reply = "✅ Entendido, es una reunión presencial."
            else:
                updated_task["status"] = "enriched"
                updated_task["next_slot"] = "datetime"
                reply = "✅ Entendido, es una reunión presencial. ¿A qué hora será el evento?"

        # Caso: usuario no tiene/ no necesita link
        elif any(keyword in user_msg_lower for keyword in negative_link_keywords):
            updated_task["meeting_link"] = "no especificado"
            updated_task["meeting_type"] = updated_task.get("meeting_type") or "virtual"
            if has_datetime:
                updated_task["status"] = "completed"
                updated_task.pop("next_slot", None)
                reply = "✅ Entendido, dejaré la liga como no especificada."
            else:
                updated_task["status"] = "enriched"
                updated_task["next_slot"] = "datetime"
                reply = "✅ Entendido, dejaré la liga como no especificada. ¿A qué hora será el evento?"

        # Caso: usuario pasa directamente una URL
        elif url_match := re.search(r"https?://\S+", user_message):
            updated_task["meeting_link"] = url_match.group(0)
            updated_task["meeting_type"] = "virtual"
            if has_datetime:
                updated_task["status"] = "completed"
                updated_task.pop("next_slot", None)
                reply = "✅ Listo, ya agregué la liga al evento."
            else:
                updated_task["status"] = "enriched"
                updated_task["next_slot"] = "datetime"
                reply = "✅ Listo, ya agregué la liga al evento. ¿A qué hora será?"

        else:
            # No entendimos nada útil → seguir pidiendo la liga
            updated_task["status"] = "created"
            updated_task["next_slot"] = "meeting_link"
            reply = "🔗 ¿Podrías compartirme la liga de la reunión?"

    # -------------------------------------------------
    # SLOT: datetime
    # -------------------------------------------------
    elif pending_field == "datetime":
        from app.services.datetime_normalizer_service import normalize_datetime_from_text

        dt = normalize_datetime_from_text(text=user_message)
        if not dt.get("hora"):
            extracted_time = _extract_time_from_text(user_message)
            if extracted_time:
                dt["hora"] = extracted_time
        has_date = _has_explicit_date(user_message)
        prev_fecha = updated_task.get("fecha")

        if dt.get("fecha") and dt.get("hora"):
            # Siempre guardamos hora
            updated_task["hora"] = dt["hora"]
            # Solo pisar fecha si el usuario dio fecha explicita
            if prev_fecha and not has_date:
                updated_task["fecha"] = prev_fecha
            else:
                updated_task["fecha"] = dt["fecha"]
            updated_task["status"] = "completed"
            updated_task.pop("next_slot", None)
            reply = (
                f"??? Perfecto, evento agendado para {updated_task.get('fecha')} "
                f"a las {updated_task.get('hora')}."
            )

        elif dt.get("fecha"):
            updated_task["fecha"] = dt["fecha"]
            updated_task["status"] = "enriched"
            updated_task["next_slot"] = "datetime"
            reply = f"???? Fecha guardada: {dt['fecha']}. ??A qu?? hora ser???"

        elif dt.get("hora"):
            updated_task["hora"] = dt["hora"]
            updated_task["status"] = "enriched"
            updated_task["next_slot"] = "datetime"
            reply = f"???? Hora guardada: {dt['hora']}. ??Para qu?? d??a?"

        else:
            updated_task["status"] = "created"
            updated_task["next_slot"] = "datetime"
            reply = (
                "No pude entender la fecha u hora. "
                "Por ejemplo: 'ma??ana a las 10 am' o 'el viernes a las 3 pm'."
            )

    # -------------------------------------------------
    # SLOT DESCONOCIDO / COMENTARIO EXTRA
    # -------------------------------------------------
    else:
        updated_task["description"] = user_message.strip()
        updated_task["status"] = "completed"
        updated_task.pop("next_slot", None)
        reply = "✅ Perfecto, ya agregué el comentario a la tarea."

    return {
        "reply": reply,
        "updated_task": updated_task,
    }


def continue_task(*, state: Any, user_message: str) -> Dict[str, Any]:
    """
    Consume el estado conversacional y la respuesta del usuario.
    Si aún hay slots pendientes → task_followup.
    Si ya está completa → persiste tarea, genera ICS y cierra estado.
    """
    pending_field = getattr(state, "awaiting_slot", None)
    task_snapshot = getattr(state, "slots", {}) or {}

    result = handle_task_continuation(
        user_message=user_message,
        pending_field=pending_field or "",
        task_snapshot=task_snapshot,
    )

    updated = result.get("updated_task", {})
    next_slot = updated.get("next_slot")

    # -------------------------------------------------
    # Aún falta información → FOLLOW-UP
    # -------------------------------------------------
    if updated.get("status") != "completed" and next_slot:
        state.intent = "task_enrichment"
        state.awaiting_slot = next_slot
        state.slots = updated

        return {
            "action": "task_followup",
            "task": {
                **updated,
                "needs_followup": True,
                "enrichment_candidates": [next_slot],
            },
        }

    # -------------------------------------------------
    # Tarea COMPLETA → persistir
    # -------------------------------------------------
    task_type = (
        updated.get("task_type")
        or task_snapshot.get("task_type")
        or updated.get("type")
        or "note"
    )

    task = Task(
        user_key=(updated.get("user_key") or task_snapshot.get("user_key") or getattr(state, "user_key", "") or ""),
        type=task_type,
        content=synthesize_task_content(updated.get("content", task_snapshot.get("content", ""))),
        description=updated.get("description"),
        meeting_type=updated.get("meeting_type"),
        meeting_link=updated.get("meeting_link"),
        location=(
            updated.get("location")
            or updated.get("ubicacion")
            or task_snapshot.get("location")
            or task_snapshot.get("ubicacion")
            or ("No especificado" if task_type in ("calendar", "reminder") else None)
        ),
        fecha=updated.get("fecha"),
        hora=updated.get("hora"),
        status="active",
    )

    add_task(task)

    # -------------------------------------------------
    # Generar ICS (solo calendar / reminder)
    # -------------------------------------------------
    ics_payload = None
    if task.type in ("calendar", "reminder"):
        try:
            ics_payload = generate_ics_for_task(task)
        except Exception:
            ics_payload = None

    # -------------------------------------------------
    # Reset total del estado conversacional
    # -------------------------------------------------
    state.intent = None
    state.awaiting_slot = None
    state.slots = {}

    tasks_grouped = get_tasks_grouped(task.user_key)

    return {
        "action": "task",
        "task": task.__dict__,
        "tasks": {
            "calendar": [t.__dict__ for t in tasks_grouped["calendar"]],
            "reminder": [t.__dict__ for t in tasks_grouped["reminder"]],
            "note": [t.__dict__ for t in tasks_grouped["note"]],
        },
        "ics": ics_payload,
    }
