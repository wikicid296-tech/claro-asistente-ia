# backend/app/services/cerebro_service.py

import logging
import re
from typing import Dict, Any

from app.services.content_safety_service import check_content_safety
from app.services.chat_orchestrator_service import run_web_chat
from app.services.web_search_service import run_web_search

from app.services.prompt_service import (
    is_aprende_intent,
    is_telcel_intent,
    is_claro_intent,
)

from app.services.aprende_search_service import run_aprende_flow
from app.agents.telcel.telcel_agent import TelcelAgent
from app.agents.claro.claro_agent import ClaroAgent

from app.states.conversationStore import load_state, save_state

logger = logging.getLogger(__name__)


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
            response_text += (
                f"**También encontré {len(all_candidates) - 1} cursos más:**\n"
            )
            for i, candidate in enumerate(all_candidates[1:4], 2):
                cand_name = candidate.get("courseName", "Curso sin nombre")
                cand_id = candidate.get("courseId", "")
                response_text += f"{i}. **{cand_name}** (Numero de curso: {cand_id})\n"
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
        "relevant_urls": [course_url],

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
) -> Dict[str, Any]:
    """
    Núcleo conversacional del sistema.
    Retorna exactamente el mismo payload que antes devolvía /chat.
    """

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
    # Cargar estado conversacional
    # -------------------------------------------------
    state = load_state(user_key)
    
    # -------------------------------------------------
    # BÚSQUEDA WEB (acción explícita)
    # -------------------------------------------------
    if action == "busqueda_web":
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
    # CHAT NORMAL (fallback)
    # -------------------------------------------------
    return run_web_chat(
        user_message=user_message,
        action=action,
        user_key=user_key,
    )
