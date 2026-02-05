from typing import Dict, Any, Optional

from app.agents.task.calendar_agent import CalendarTaskAgent
from app.agents.task.reminder_agent import ReminderTaskAgent
from app.agents.task.note_agent import NoteAgent as NoteTaskAgent

from app.domain.task import Task
from app.stores.task_store import add_task, get_tasks_grouped
from app.services.task_analysis_service import analyze_task
from app.services.task_calendar_service import generate_ics_for_task


# ============================================================
# Helpers
# ============================================================
def _select_agent(ttype: str):
    if ttype == "calendar":
        return CalendarTaskAgent()
    if ttype == "reminder":
        return ReminderTaskAgent()
    return NoteTaskAgent()


def _followup_question_for(slot: Optional[str], ttype: str) -> str:
    """
    Pregunta determinista para follow-up, alineada a slots soportados.
    """
    if slot == "meeting_link":
        return "🔗 ¿Ya tienes la liga de la reunión?"
    if slot == "datetime":
        # usable tanto para calendar como reminder
        if ttype == "reminder":
            return "⏰ ¿Qué día y a qué hora quieres que te lo recuerde?"
        return "🕒 ¿En qué fecha y hora será el evento?"
    # fallback
    return "🤔 ¿Puedes darme un poco más de información?"


def _normalize_enrichment_candidates(ttype: str, candidates: list) -> list:
    """
    Normaliza candidatos a un set de slots que tu continuation service soporta.
    Tu task_continuation_service soporta explícitamente: meeting_link, datetime.
    """
    if not isinstance(candidates, list):
        return []

    # Si el agente manda fecha/hora para reminders, lo convertimos a datetime
    if ttype in ("reminder", "calendar"):
        if ("fecha" in candidates) or ("hora" in candidates):
            # conserva meeting_link si también existe, pero datetime debe existir
            normalized = []
            if "meeting_link" in candidates:
                normalized.append("meeting_link")
            normalized.append("datetime")
            return normalized

    # si ya viene datetime/meeting_link, mantenemos orden (meeting_link primero si existe)
    if "meeting_link" in candidates and "datetime" in candidates:
        return ["meeting_link", "datetime"]

    return candidates


# ============================================================
# Core Orchestrator
# ============================================================
def process_task(
    *,
    normalized: str,
    ttype: str,
    state: Any,
    user_key: str = "",
) -> Dict[str, Any]:
    """
    Orquesta la creación de tareas.
    - Analiza slots mínimos
    - Ejecuta agente (aquí "nace" la tarea)
    - Decide follow-up / cierre
    - Persiste tarea si está completa
    """

    print("\n================ TASK ORCHESTRATOR ================")
    print("📥 NORMALIZED TEXT:", normalized)
    print("📥 TASK TYPE:", ttype)

    # -------------------------------------------------
    # 1) Analizar intención / slots (⚠️ firma real: text, task_type)
    # -------------------------------------------------
    analysis = analyze_task(
        text=normalized,
        task_type=ttype,
    )

    print("\n🧠 ANALYSIS RESULT:")
    print(analysis)

    # -------------------------------------------------
    # 2) Seleccionar agente
    # -------------------------------------------------
    agent = _select_agent(ttype)
    print("\n🤖 AGENT SELECTED:", agent.__class__.__name__)

    # -------------------------------------------------
    # 3) Ejecutar agente (AQUÍ NACE LA TAREA)
    # -------------------------------------------------
    agent_result = agent.handle(
        content=normalized,
        analysis=analysis,
        state=state,
    )

    print("\n📤 AGENT RESULT:")
    print(agent_result)

    # -------------------------------------------------
    # 4) Follow-up requerido (FUENTE ÚNICA: AGENTE)
    #    + NORMALIZACIÓN de slots para compat con continuation
    # -------------------------------------------------
    if agent_result.get("needs_followup"):
        print("\n🟡 FOLLOW-UP REQUIRED")

        raw_candidates = agent_result.get("enrichment_candidates", []) or []
        candidates = _normalize_enrichment_candidates(ttype, raw_candidates)

        # Persistimos en estado el snapshot que el continuation entiende
        state.intent = "task_enrichment"
        state.awaiting_slot = candidates[0] if candidates else None

        state.slots = {
            **agent_result,
            "task_type": ttype,
        }

        # Garantía: followup_question NO nulo
        followup_q = _followup_question_for(state.awaiting_slot, ttype)
        agent_result["followup_question"] = followup_q

        # También reflejar candidates normalizados para el front/debug
        agent_result["enrichment_candidates"] = candidates

        print("🧭 STATE UPDATED:")
        print("intent:", state.intent)
        print("awaiting_slot:", state.awaiting_slot)
        print("slots:", state.slots)

        ret = {
            "action": "task_followup",
            "task": agent_result,
        }
        print("\n🔁 RETURN (followup):")
        print(ret)
        return ret

    # -------------------------------------------------
    # 5) Tarea completa → persistir en backend
    # -------------------------------------------------
    print("\n🟢 TASK COMPLETED (NO FOLLOW-UP)")

    # preferir user_key explícito (viene del cerebro); fallback a state.user_key
    final_user_key = user_key or getattr(state, "user_key", "") or ""
    safe_task_type = ttype if ttype in ("calendar", "reminder", "note") else "note"

    task_entity = Task(
        user_key=final_user_key,
        type=safe_task_type,
        content=agent_result.get("content"),
        description=analysis.get("description"),
        fecha=agent_result.get("fecha") or analysis.get("fecha"),
        hora=agent_result.get("hora") or analysis.get("hora"),
        meeting_type=analysis.get("meeting_type"),
        meeting_link=analysis.get("meeting_link"),
        location=(
            agent_result.get("ubicacion")
            or agent_result.get("lugar")
            or analysis.get("location")
        ),
        status="active",
    )

    add_task(task_entity)
    print("💾 TASK PERSISTED:", task_entity)

    tasks_grouped = get_tasks_grouped(final_user_key)

    # Mantengo tu comportamiento actual (ics string) para no romper el front:
    ics = generate_ics_for_task(task_entity)

    ret = {
        "action": "task",
        "task": task_entity.__dict__,
        "tasks": {
            "calendar": [t.__dict__ for t in tasks_grouped["calendar"]],
            "reminder": [t.__dict__ for t in tasks_grouped["reminder"]],
            "note": [t.__dict__ for t in tasks_grouped["note"]],
        },
        "ics": ics,
    }

    print("\n🔁 RETURN (process_task final):")
    print(ret)

    return ret


# ============================================================
# Public entrypoint called by cerebro_service
# ============================================================
def handle_task_web(
    *,
    # formato viejo (actual en tu cerebro_service)
    user_message: str,
    normalized: Optional[str] = None,
    ttype: Optional[str] = None,
    # formato nuevo (si luego migras el cerebro)
    user_key: Optional[str] = None,
    task_type: Optional[str] = None,
    # estado
    state: Any,
    continuation: bool = False,
    **_ignored: Any,  # tolerancia a params legacy extra
) -> Dict[str, Any]:
    """
    Wrapper tolerante para compatibilidad.
    Acepta tanto:
      - (user_message, normalized, ttype, state)
      - (user_message, user_key, task_type, state)
    """

    print("🧾 USER MESSAGE:", user_message)

    # decidir texto normalizado y tipo
    normalized_text = (normalized or user_message or "").strip()
    final_ttype = (task_type or ttype or "").strip()

    if not final_ttype:
        raise ValueError("handle_task_web: task_type/ttype es requerido")

    # si en el futuro quieres continuar desde aquí, lo soportamos
    if continuation:
        # tu cerebro ya usa continue_task directamente,
        # así que por ahora lo dejamos como error explícito para evitar doble lógica.
        raise ValueError("handle_task_web: continuation debe manejarse vía continue_task en cerebro_service")

    result = process_task(
        normalized=normalized_text,
        ttype=final_ttype,
        state=state,
        user_key=user_key or "",
    )

    print("\n🔁 RETURN (handle_task_web):")
    print(result)
    return result
