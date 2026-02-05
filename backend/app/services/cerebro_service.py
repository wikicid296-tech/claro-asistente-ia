# backend/app/services/cerebro_service.py

import logging
import re
from datetime import datetime, timedelta, date
from typing import Dict, Any, cast, Optional, Tuple

from app.services.channel_message_service import build_chat_messages
from app.services.prompt_service import build_system_prompt
from app.services.context_service import get_context_for_query
from app.services.task_calendar_service import generate_ics_for_task
from app.domain.task import Task
from app.stores.task_store import add_task, get_tasks_grouped

from app.services.content_safety_service import check_content_safety
from app.services.chat_orchestrator_service import run_web_chat
from app.services.web_search_service import run_web_search
from app.services.freshness_llm_service import llm_can_answer_with_cutoff
from app.services.memory_service import (
    append_memory,
    build_prompt_messages,
)
from app.services.intent_clasification_service import classify_intent

from app.services.prompt_service import (
    is_aprende_intent,
    is_telcel_intent,
    is_claro_intent,
)

from app.services.aprende_search_service import run_aprende_flow
from app.agents.telcel.telcel_agent import TelcelAgent
from app.agents.claro.claro_agent import ClaroAgent

from app.states.conversationStore import load_state, save_state
from app.services.task_orchestator_service import handle_task_web
from app.services.task_continuation_service import handle_task_continuation, continue_task

logger = logging.getLogger(__name__)


# =========================================================
# TASK RESPONSE HELPERS (compat layer)
# =========================================================
def _confirmation_text(task: Dict[str, Any]) -> str:
    ttype = None
    # task may be nested or the dict itself may contain task_type
    if isinstance(task, dict):
        ttype = task.get("task_type") or task.get("type")

    if ttype == "calendar":
        return "📅 Listo. Guardé el evento."
    if ttype == "reminder":
        return "⏰ Listo. Guardé el recordatorio."
    if ttype == "note":
        return "📝 Nota guardada."

    return "✅ Listo. Guardé la tarea."


def _build_task_response(task_result: Dict[str, Any], state) -> Dict[str, Any]:
    """
    Construye la respuesta final basada en el resultado del task orchestrator.
    Esta función actúa como capa de compatibilidad entre diferentes formatos
    de `task_result` que pueden venir del orquestador.
    """
    logger.info("📤 CONSTRUYENDO RESPUESTA DE TAREA (compat)")
    logger.info(f"📦 TASK RESULT: {task_result}")
    logger.info(f"📦 action={task_result.get('action')}")

    # Manejar distintos shapes: new style: { action, task }, old style: { needs_followup, enrichment_candidates, ... }
    action = task_result.get("action")
    task = task_result.get("task") or task_result

    # Legacy follow-up flag
    needs_followup = task_result.get("needs_followup") or (action == "task_followup")

    if needs_followup:
        enrichment = task_result.get("enrichment_candidates") or task.get("enrichment_candidates") or []
        awaiting_slot = enrichment[0] if enrichment else None

        # 1) Preferir followup_question producido por el orquestador/agente
        # (soporta shapes anidados: task_result.task.task.followup_question)
        followup_text = None
        try:
            followup_text = (
                (task.get("followup_question"))
                or (task_result.get("followup_question"))
                or ((task.get("task") or {}).get("followup_question"))
            )
        except Exception:
            followup_text = None

        # 2) Fallback legacy si no vino followup_question (compat)
        if not followup_text:
            FOLLOWUP_QUESTIONS = {
                "meeting_link": "🔗 ¿Ya tienes la liga de la reunión?",
                # 'datetime' es genérico; el copy correcto debe venir del orquestador
                "datetime": "🕒 ¿En qué fecha y hora?",
            }
            followup_text = FOLLOWUP_QUESTIONS.get(
                awaiting_slot or "",
                "🤔 ¿Puedes darme un poco más de información?"
            )

        return {
            "success": True,
            "response": followup_text,
            "context": "🗓️ GESTIÓN DE TAREAS",
            "context_reset": False,
            "action": "task_followup",
            "task": task_result,
            "task_type": task.get("task_type")
        }

    # Confirmación final
    return {
        "success": True,
        "response": _confirmation_text(task),
        "context": "🗓️ GESTIÓN DE TAREAS",
        "context_reset": False,
        "action": "task",
        "task": task_result,
    }


# =====================================================
# Helpers locales (extraídos del controller)
# =====================================================

def build_aprende_iframe_response(
    user_message: str,
    top_course: Dict[str, Any],
    all_candidates: list[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Construye la respuesta rica que espera la web
    (iframe Aprende.org).
    """
    course_id = top_course.get("courseId", "")
    course_name = top_course.get("courseName", "Curso disponible")
    score = top_course.get("score", 0.0)

    course_url = (
        f"https://aprende.org/cursos/{course_id}"
        if course_id else "https://aprende.org"
    )

    if score > 0.35 and all_candidates:
        response_text = (
            f"🎓 Encontré {len(all_candidates)} cursos relacionados con "
            f"'{user_message}':\n\n"
            f"**{course_name}** (Numero de curso: {course_id})\n\n"
        )

        if len(all_candidates) > 1:
            response_text = (
                f"**También encontré {len(all_candidates) - 1} cursos más:**\n"
            )
            for i, candidate in enumerate(all_candidates[1:4], 2):
                cand_name = candidate.get("courseName", "Curso sin nombre")
                cand_id = candidate.get("courseId", "")
                response_text = f"{i}. **{cand_name}** (Numero de curso: {cand_id})\n"
    else:
        response_text = (
            f"😕 No encontré cursos relacionados con '{user_message}'. "
            f"¿Podrías intentar con otras palabras clave?"
        )
        course_url = None

    return {
        "success": True,
        "response": response_text,
        "aprende_ia_used": True,
        "context": "🎓 ÁREA: EDUCACIÓN Y DESARROLLO PROFESIONAL (Aprende.org)",
        "context_reset": False,
        "memory_used": 0,
        "relevant_urls": [course_url] if course_url else [],

        "tipo_contenido": "webpage",
        "tipo_recurso": "curso",
        "url_pdf": "",
        "url_recurso": course_url,
        "url_video": "",

        "query": user_message,
        "candidates": all_candidates[:10],
        "top": [top_course],
    }


# =====================================================
# Servicio principal
# =====================================================

def procesar_chat_web(
    *,
    user_message: str,
    action: str,
    user_key: str,
    macro_intent: str | None = None,
    task_type: str | None = None,
) -> Dict[str, Any]:
    """
    Núcleo conversacional del sistema.
    Retorna exactamente el mismo payload que antes devolvía /chat.
    """
    logger.info("🧠 procesar_chat_web INVOCADO")
    logger.info(f"➡️ user_message='{user_message}'")
    logger.info(f"➡️ action='{action}', user_key='{user_key}'")

    # -------------------------------------------------
    # Content Safety (global)
    # -------------------------------------------------
    try:
        safety = check_content_safety(user_message)
    except Exception:
        logger.exception("Error ejecutando content safety")
        safety = {"flagged": False}

    if safety.get("flagged"):
        return {
            "success": False,
            "type": "blocked",
            "message": "No puedo ayudar con este tipo de contenido.",
        }

    # -------------------------------------------------
    # Guardar mensaje en memoria
    # -------------------------------------------------
    append_memory(
        user_key=user_key,
        role="user",
        message=user_message,
    )

    # -------------------------------------------------
    # Cargar estado conversacional
    # -------------------------------------------------
    state = load_state(user_key)

    # -------------------------------------------------
    # FIX: asegurar user_key en state para capas posteriores
    # -------------------------------------------------
    try:
        if not getattr(state, "user_key", None):
            setattr(state, "user_key", user_key)
    except Exception:
        # Fallback si state es dict-like en algun entorno
        try:
            state["user_key"] = user_key
        except Exception:
            pass
    
    logger.info(f"🔍 Estado actual: intent={state.intent}, awaiting_slot={state.awaiting_slot}")
    logger.info(f"🔍 State.slots snapshot: {state.slots}")

    # -------------------------------------------------
    # CANCELACIÓN GLOBAL DE TAREA (chequear de inmediato)
    # -------------------------------------------------
    CANCEL_PATTERNS = (
        "cancelar",
        "olvida",
        "ya no",
        "mejor no",
        "detener",
        "cancela",
    )

    if any(p in (user_message or "").lower() for p in CANCEL_PATTERNS):
        logger.info("❌ Cancelación detectada por el usuario")

        state.intent = None
        state.awaiting_slot = None
        state.slots = {}
        save_state(user_key, state)

        return {
            "success": True,
            "response": "❌ Creación de evento cancelada.",
            "context": "🗓️ GESTIÓN DE TAREAS",
            "context_reset": False,
            "action": "task_cancelled",
        }

    # -------------------------------------------------
    # CONSULTA DE TAREAS (task_query) - PRIORIDAD ABSOLUTA
    # ⚠️ NO DEBE DEPENDER DE LLM
    # -------------------------------------------------
    def _parse_task_date(task: Task) -> Optional[date]:
        if not getattr(task, "fecha", None):
            return None
        try:
            return datetime.strptime(task.fecha, "%Y-%m-%d").date()
        except Exception:
            return None

    def _detect_date_range(text: str) -> Tuple[Optional[date], Optional[date], Optional[str]]:
        today = date.today()

        if "pasado mañana" in text or "pasado manana" in text:
            target = today + timedelta(days=2)
            return target, target, "pasado mañana"

        if "mañana" in text or "manana" in text:
            target = today + timedelta(days=1)
            return target, target, "mañana"

        if "hoy" in text:
            return today, today, "hoy"

        if "esta semana" in text:
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
            return start, end, "esta semana"

        m = re.search(r"pr[oó]ximos?\s+(\d+)\s+d[ií]as", text)
        if m:
            try:
                days = int(m.group(1))
            except Exception:
                days = 0
            if days > 0:
                start = today
                end = today + timedelta(days=days - 1)
                label = f"próximos {days} días"
                return start, end, label

        return None, None, None

    def _build_task_table(
        calendar_tasks: list[Task],
        reminder_tasks: list[Task],
        notes_tasks: list[Task],
    ) -> str:
        max_rows_per_type = 10

        def _sanitize(value: Optional[str]) -> str:
            if not value:
                return "-"
            return str(value).replace("|", " / ").replace("\n", " ").strip() or "-"

        def _normalize_title(content: Optional[str]) -> str:
            if not content:
                return "-"
            raw = str(content).strip()
            words = raw.split()
            if not words:
                return "-"

            # Remover prefijos instruccionales comunes, sin truncar títulos válidos.
            prefixes = {
                "recuerdame", "recuérdame", "recordar", "recordatorio",
                "agenda", "agendar", "evento", "cita",
                "nota", "anota", "apunta", "escribe",
            }
            first = words[0].lower()
            if first in prefixes and len(words) > 1:
                title = " ".join(words[1:])
            else:
                title = raw

            title = title.strip(" -:,.")
            if not title:
                return "-"
            return title[0].upper() + title[1:]

        def _format_created_at(task: Task) -> str:
            ts = getattr(task, "created_at", None)
            if ts is None:
                return "-"
            try:
                return datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d")
            except Exception:
                return "-"

        def _get_date(task: Task) -> Optional[date]:
            return _parse_task_date(task)

        def _get_time(task: Task) -> Optional[str]:
            hora = getattr(task, "hora", None)
            return hora if hora else None

        def _is_today(task: Task) -> bool:
            dt = _get_date(task)
            return bool(dt and dt == date.today())

        def _is_tomorrow(task: Task) -> bool:
            dt = _get_date(task)
            return bool(dt and dt == date.today() + timedelta(days=1))

        def _status_label(task: Task) -> str:
            if _is_today(task):
                return "hoy"
            if _is_tomorrow(task):
                return "mañana"
            return _sanitize(getattr(task, "status", None))

        def _sort_key(task: Task) -> tuple:
            dt = _get_date(task)
            hora = _get_time(task) or "23:59"
            if dt:
                return (0, dt, hora)
            created = getattr(task, "created_at", 0.0) or 0.0
            return (1, datetime.fromtimestamp(float(created)).date(), "23:59")

        def _build_table_for_type(tasks: list[Task], tlabel: str) -> str:
            if not tasks:
                return f"### {tlabel}\nSin tareas.\n"

            ordered = sorted(tasks, key=_sort_key)
            total = len(ordered)
            visible = ordered[:max_rows_per_type]

            lines = [
                f"### {tlabel} ({total})",
                "| Título | Fecha | Hora | Ubicación/Link | Creado |",
                "| --- | --- | --- | --- | --- |",
            ]

            for t in visible:
                title = _normalize_title(getattr(t, "content", None))
                fecha = _sanitize(getattr(t, "fecha", None))
                hora = _sanitize(getattr(t, "hora", None))
                meeting_type = getattr(t, "meeting_type", None)
                meeting_link = _sanitize(getattr(t, "meeting_link", None))
                location = _sanitize(getattr(t, "location", None))
                if meeting_type == "virtual":
                    place = f"Link: {meeting_link}" if meeting_link != "-" else "-"
                elif meeting_type == "presencial":
                    place = f"Ubicación: {location}" if location != "-" else "-"
                else:
                    if meeting_link != "-":
                        place = f"Link: {meeting_link}"
                    elif location != "-":
                        place = location
                    else:
                        place = "-"
                created_at = _format_created_at(t)
                lines.append(
                    f"| {title} | {fecha} | {hora} | {place} | {created_at} |"
                )

            if total > max_rows_per_type:
                remaining = total - max_rows_per_type
                lines.append("")
                lines.append(f"Mostrando {max_rows_per_type} de {total}. Faltan {remaining}.")

            lines.append("")
            return "\n".join(lines)

        return "\n".join([
            _build_table_for_type(calendar_tasks, "Eventos"),
            _build_table_for_type(reminder_tasks, "Recordatorios"),
            _build_table_for_type(notes_tasks, "Notas"),
        ]).strip()

    QUERY_PATTERNS = (
        "qué hay",
        "que hay",
        "cuántas",
        "cuantos",
        "tenemos",
        "muéstrame",
        "mostrar",
        "lista",
        "agenda hoy",
        "tareas activas",
        "recordatorios",
        "que eventos tengo",
        "mi agenda",
        "esta semana",
    )

    normalized_message = (user_message or "").lower()
    logger.info("🔎 Evaluando task_query (early) contra: '%s'", normalized_message)

    if any(p in normalized_message for p in QUERY_PATTERNS):
        logger.info("📊 TASK QUERY detectado (early)")

        tasks = get_tasks_grouped(user_key)

        start_date, end_date, range_label = _detect_date_range(normalized_message)
        if start_date and end_date:
            logger.info("🗓️ Rango detectado: %s -> %s (%s)", start_date, end_date, range_label)
        else:
            logger.info("🗓️ Sin rango detectado para task_query")

        calendar_tasks = tasks.get("calendar", [])
        reminder_tasks = tasks.get("reminder", [])
        notes_tasks = tasks.get("note", [])

        if start_date and end_date:
            calendar_tasks = [
                t for t in calendar_tasks
                if (dt := _parse_task_date(t)) and start_date <= dt <= end_date
            ]
            reminder_tasks = [
                t for t in reminder_tasks
                if (dt := _parse_task_date(t)) and start_date <= dt <= end_date
            ]

        total_calendar = len(calendar_tasks)
        total_reminder = len(reminder_tasks)
        total_notes = len(notes_tasks)

        if range_label:
            response_text = (
                f"📅 Para {range_label}, tienes {total_calendar} eventos y "
                f"{total_reminder} recordatorios activos."
                f" Además, has guardado {total_notes} notas."
            )
        else:
            response_text = (
                f"📅 Tienes {total_calendar} eventos y "
                f"{total_reminder} recordatorios activos."
                f" Además, has guardado {total_notes} notas."
            )

        table_text = _build_task_table(calendar_tasks, reminder_tasks, notes_tasks)

        return {
            "success": True,
            "response": f"{response_text}\n\n{table_text}",
            "context": "🗓️ GESTIÓN DE TAREAS",
            "context_reset": False,
            "action": "task_query",
            "tasks": {
                "calendar": [t.__dict__ for t in calendar_tasks],
                "reminder": [t.__dict__ for t in reminder_tasks],
                "note": [t.__dict__ for t in notes_tasks],
            },
        }

    # -------------------------------------------------
    # Analizar contexto via LLM/service para detectar macro intent y task_type
    # (compatibilidad: preferir parámetros explícitos si vienen desde el controller)
    try:
        context = get_context_for_query(user_message)
    except Exception:
        context = {}

    macro_intent = macro_intent or context.get("macro_intent")
    task_type = task_type or context.get("task_type")
    
    # ============================================================
    # 🧠 DETECCIÓN DE INTENCIÓN POR LLM (override de front)
    # ============================================================
    # Nota: el frontend suele mandar action='descubre'. Queremos ejecutar
    # la clasificación por LLM cuando el front pide 'descubre' o cuando
    # macro_intent no fue provisto explícitamente.
    if not macro_intent or macro_intent == "descubre" or action == "descubre":
        try:
            logger.info("🧠 Ejecutando clasificación de intención por LLM (action=%s, macro_intent=%s)", action, macro_intent)
            intent = classify_intent(user_message)
            macro_intent = intent.get("macro_intent") or macro_intent
            task_type = intent.get("task_type")

            logger.info(
                "🧠 LLM intent detected → macro_intent=%s, task_type=%s",
                macro_intent,
                task_type
            )
        except Exception as e:
            logger.exception("❌ Error en LLM intent detection")

    logger.info(f"📊 Intención detectada: macro_intent={macro_intent}, task_type={task_type}")

    # -------------------------------------------------
    # CONTINUACIÓN DE TAREA (PRIORIDAD ABSOLUTA)
    # ⚠️ NADA puede competir con este flujo
    # -------------------------------------------------
    if state.intent == "task_enrichment" and state.awaiting_slot:
        logger.info("🧠 PRIORIDAD: task_enrichment activo")
        logger.info(f"➡️ Awaiting slot: {state.awaiting_slot}")
        logger.info(f"➡️ User message (raw): {user_message}")

        result = continue_task(state=state, user_message=user_message)

        logger.info(f"🧪 Resultado continue_task action={result.get('action')}")
        logger.info(f"🧪 Resultado completo continue_task: {result}")

        if result.get("action") == "task_followup":
            logger.info("🔄 Follow-up continúa, no evaluar otros intents")
            task = result.get("task", {})
            enrichment = task.get("enrichment_candidates") or []
            awaiting_slot = enrichment[0] if enrichment else None

            FOLLOWUP_QUESTIONS = {
                "meeting_link": "🔗 ¿Ya tienes la liga de la reunión?",
                "datetime": "🕒 ¿A qué hora será el evento?",
            }

            followup_text = FOLLOWUP_QUESTIONS.get(awaiting_slot or "", "🤔 ¿Puedes darme un poco más de información?")

            # Persistir estado (si aplica) y devolver follow-up
            if awaiting_slot:
                state.intent = "task_enrichment"
                state.awaiting_slot = awaiting_slot
                state.slots = state.slots or {}
                save_state(user_key, state)

            return {
                "success": True,
                "response": followup_text,
                "context": "🗓️ GESTIÓN DE TAREAS",
                "context_reset": False,
                "action": "task_followup",
                "task": task,
            }

        if result.get("action") == "task":
            logger.info("✅ Tarea cerrada desde follow-up")
            return {
                "success": True,
                "response": _confirmation_text(result.get("task", {})),
                "context": "🗓️ GESTIÓN DE TAREAS",
                "context_reset": False,
                "action": "task",
                "task": result.get("task"),
                "tasks": result.get("tasks"),
                "ics": result.get("ics"),
            }

        # ⛔️ CORTA EJECUCIÓN TOTAL
        return result

    # GESTIÓN DE TAREAS (macro-intent) - PRIORIDAD ALTA
    # -------------------------------------------------
    # Si el front indica macro_intent="task", procesar tarea
    if (macro_intent or "").lower() == "task":
        logger.info("🎯 PROCESANDO TAREA NUEVA")
        
        if not task_type:
            logger.error("❌ task_type no puede ser None al procesar tarea")
            return {
                "success": False,
                "response": "No se pudo determinar el tipo de tarea. Intenta de nuevo.",
                "context": "❌ ERROR",
                "context_reset": False,
            }
        
        # Normalización previa obligatoria
        normalized_text = user_message.strip()
        
        logger.info(f"📝 Procesando tarea tipo: {task_type}, texto: {normalized_text}")
        
        try:
            task_result = handle_task_web(
                user_message=user_message,
                user_key=user_key,
                state=state,
                task_type=task_type,
            )
            
            logger.info(f"🧪 Resultado handle_task_web action={task_result.get('action')}")
            logger.info(f"🧪 Payload completo handle_task_web: {task_result}")
            
            if task_result.get("action") == "task_followup":
                logger.info("???? Tarea requiere follow-up (respetar orquestador)")

                # Guardar estado para continuar (solo slots; NO decidir copy)
                task_payload = task_result.get("task", task_result)  # compat
                inner_task = task_payload.get("task") if isinstance(task_payload, dict) else None
                if isinstance(inner_task, dict):
                    enrichment_candidates = (
                        task_payload.get("enrichment_candidates")
                        or inner_task.get("enrichment_candidates")
                        or []
                    )
                else:
                    enrichment_candidates = (
                        task_payload.get("enrichment_candidates", [])
                        if isinstance(task_payload, dict)
                        else []
                    )
                awaiting_slot = enrichment_candidates[0] if enrichment_candidates else None

                if awaiting_slot:
                    state.intent = "task_enrichment"
                    state.awaiting_slot = awaiting_slot

                    # Guardar snapshot plano con campos de tarea (fecha/hora/meeting_link/etc.)
                    raw_task = task_result.get("task", {}) if isinstance(task_result, dict) else {}
                    if isinstance(raw_task, dict) and isinstance(raw_task.get("task"), dict):
                        raw_task = raw_task.get("task")

                    raw_task = {
                        **(raw_task or {}),
                        "task_type": raw_task.get("task_type") or task_type,
                        "content": raw_task.get("content") or normalized_text,
                        "user_key": user_key,
                    }

                    state.slots = cast(Any, raw_task)
                    save_state(user_key, state)

                # ??? Delegar el texto final a la capa compat que ahora prioriza followup_question
                return _build_task_response(task_result, state)

            # ??? 
            # ✅ SOLO SI EL ORQUESTADOR CONFIRMA CIERRE
            logger.info("✅ Tarea completada sin follow-up (cerrada por orquestador)")
            logger.info("🚦 Delegando respuesta final a _build_task_response")

            return _build_task_response(task_result, state)
            
        except Exception as e:
            logger.exception(f"❌ Error procesando tarea: {e}")
            return {
                "success": False,
                "response": f"Error al procesar la tarea: {str(e)}",
                "context": "❌ ERROR",
                "context_reset": False,
            }

    # -------------------------------------------------
    # BÚSQUEDA WEB (acción explícita)
    # -------------------------------------------------
    if action == "busqueda_web":
        logger.info("🌐 BÚSQUEDA WEB EXPLÍCITA")
        web_result = run_web_search(user_message)

        return {
            "success": True,
            "response": web_result.get(
                "content",
                "No fue posible obtener resultados de la búsqueda."
            ),
            "context": "🌐 BÚSQUEDA WEB",
            "context_reset": False,
            "memory_used": 0,
            "relevant_urls": web_result.get("sources", []),
            "action": "busqueda_web",
        }

    # -------------------------------------------------
    # Resolución de slot pendiente TELCEL
    # -------------------------------------------------
    if state.awaiting_slot == "telcel_subdomain":
        logger.info("📱 RESOLVIENDO SLOT TELCEL")
        telcel_agent = TelcelAgent(
            user_message=user_message,
            context=state.slots,
            intent="telcel",
        )

        result = telcel_agent.handle()
        state.awaiting_slot = None
        save_state(user_key, state)
        return result

    # -------------------------------------------------
    # Redirección Claro → Telcel (por país)
    # -------------------------------------------------
    if state.awaiting_slot == "pais" and state.intent == "claro":
        logger.info("🌎 REDIRECCIÓN CLARO → TELCEL")

        original_query = state.original_query or user_message

        if re.search(r"\bm[eé]xico\b", user_message.lower()):
            original_query = f"{original_query} mexico"

        if is_telcel_intent(user_message, action=action):
            state.awaiting_slot = None
            state.intent = None
            state.original_query = None
            save_state(user_key, state)

            telcel_agent = TelcelAgent(
                user_message=original_query,
                context={},
                intent="telcel",
            )
            return telcel_agent.handle()

    # -------------------------------------------------
    # INTENT APRENDE
    # -------------------------------------------------
    if is_aprende_intent(user_message, action=action):
        logger.info("🎓 INTENT APRENDE DETECTADO")
        aprende_result = run_aprende_flow(user_message)

        top = aprende_result.get("top") or []
        candidates = aprende_result.get("candidates") or []

        if top:
            return build_aprende_iframe_response(
                user_message=user_message,
                top_course=top[0],
                all_candidates=candidates,
            )

        return {
            "success": True,
            "response": aprende_result.get(
                "message",
                "No contamos con cursos relacionados con tu búsqueda."
            ),
            "aprende_ia_used": True,
            "candidates": [],
            "top": [],
        }

    # -------------------------------------------------
    # INTENT TELCEL
    # -------------------------------------------------
    if is_telcel_intent(user_message, action=action):
        logger.info("📱 INTENT TELCEL DETECTADO")
        telcel_agent = TelcelAgent(
            user_message=user_message,
            context=state.slots,
            intent="telcel",
        )

        result = telcel_agent.handle()

        if result.get("awaiting"):
            state.intent = "telcel"
            state.awaiting_slot = result["awaiting"]
            state.original_query = user_message
            save_state(user_key, state)

        return result

    # -------------------------------------------------
    # INTENT CLARO
    # -------------------------------------------------
    if is_claro_intent(user_message, action=action):
        logger.info("📶 INTENT CLARO DETECTADO")
        claro_agent = ClaroAgent(
            user_message=user_message,
            context=state.slots,
            intent="claro",
        )

        result = claro_agent.handle()

        if result.get("awaiting") == "pais":
            state.intent = "claro"
            state.awaiting_slot = "pais"
            state.original_query = user_message
            save_state(user_key, state)

        return result

    # -------------------------------------------------
    # AUTO BÚSQUEDA WEB (DECISIÓN LLM)
    # -------------------------------------------------
    can_answer = llm_can_answer_with_cutoff(user_message)

    if not can_answer:
        logger.info("🌐 Auto Web Search: conocimiento insuficiente según LLM")

        web_result = run_web_search(user_message)

        return {
            "success": True,
            "response": web_result.get(
                "content",
                "No fue posible obtener información actualizada."
            ),
            "context": "🌐 BÚSQUEDA WEB (AUTO)",
            "context_reset": False,
            "memory_used": 0,
            "relevant_urls": web_result.get("sources", []),
            "action": "busqueda_web_auto",
            "auto_triggered": True,
        }

    # -------------------------------------------------
    # CHAT NORMAL (fallback con memoria)
    # -------------------------------------------------
    logger.info("💬 CHAT NORMAL (fallback)")
    messages = build_prompt_messages(
        user_key=user_key,
        user_message=user_message,
    )

    response = run_web_chat(
        messages=messages,
        action=action,
    )

    # Guardar respuesta del asistente en memoria
    append_memory(
        user_key=user_key,
        role="assistant",
        message=response.get("response", ""),
    )

    return response
