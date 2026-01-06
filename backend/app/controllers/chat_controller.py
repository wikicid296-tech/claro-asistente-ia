import logging
import os
import re
from flask import jsonify, request
from dotenv import load_dotenv
from typing import Any, Dict, List

from app.controllers._request_utils import get_user_key_from_request
from app.services.usage_service import is_usage_blocked, get_usage_status
from app.services.chat_orchestrator_service import run_web_chat
from app.services.content_safety_service import check_content_safety

from app.services.prompt_service import (
    is_aprende_intent,
    is_telcel_intent,
    is_claro_intent,
)
from app.services.aprende_search_service import run_aprende_flow
from app.services.telcel_rag_service import TelcelRAGService
from app.services.response_synthesis_service import synthesize_answer
from app.services.groq_service import get_groq_client, get_groq_api_key

from app.agents.telcel.telcel_agent import TelcelAgent
from app.agents.claro.claro_agent import ClaroAgent
from app.agents.claro.country_detector import detect_country

from app.states.conversationStore import load_state, save_state

load_dotenv()
logger = logging.getLogger(__name__)

def build_aprende_iframe_response(user_message: str, top_course: Dict[str, Any],
                                 all_candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Construye respuesta simplificada para mostrar curso en iframe.
    Solo necesita los campos mínimos que el frontend espera.
    """
    print("ESTO TRAE TOP COURSE 👾👾👾👾👾👾👾👾👾👾👾👾👾😎😎😎😎😎😎😎:", top_course)
    course_id = top_course.get('courseId', '')
    course_name = top_course.get('courseName', 'Curso disponible')
    mejor_score = top_course.get('score', 0.0)
    print(f"Mejor curso: {course_name} (ID: {course_id}) con score✅✅ {mejor_score}")

    course_url = f"https://aprende.org/cursos/{course_id}" if course_id else "https://aprende.org"

    if mejor_score > 0.35:
        if all_candidates:
            response_text = f"🎓 Encontré {len(all_candidates)} cursos relacionados con '{user_message}':\n\n"
            response_text += f"**{course_name}** (Numero de curso: {course_id})\n\n"

            if len(all_candidates) > 1:
                response_text += f"**También encontré {len(all_candidates) - 1} cursos más:**\n"
                for i, candidate in enumerate(all_candidates[1:4], 2):
                    cand_name = candidate.get('courseName', 'Curso sin nombre')
                    cand_id = candidate.get('courseId', '')
                    response_text += f"{i}. **{cand_name}** (Numero de curso: {cand_id})\n"
        else:
            response_text = f"😕 No encontré cursos relacionados con '{user_message}'. ¿Podrías intentar con otras palabras clave?"
    else:
        response_text = f"😕 No encontré cursos relacionados con '{user_message}'. ¿Podrías intentar con otras palabras clave?"
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
        "top": [top_course]
    }


def chat_controller():
    """
    Controller principal del endpoint /chat.
    Implementa estado conversacional mínimo (slots + awaiting).
    """

    data = request.get_json(force=True, silent=True) or {}
    user_message = (data.get("message") or "").strip()
    action = data.get("action", "busqueda")
    user_key =  get_user_key_from_request()

    if not user_message:
        return jsonify({
            "success": False,
            "message": "Mensaje vacío"
        }), 400

    # =====================================================
    # CONTENT SAFETY (GLOBAL)
    # =====================================================
    try:
        safety = check_content_safety(user_message)
    except Exception:
        logger.exception("Error ejecutando content safety")
        safety = {"flagged": False}

    if safety.get("flagged"):
        return jsonify({
            "success": False,
            "type": "blocked",
            "message": "No puedo ayudar con este tipo de contenido."
        }), 200

    # =====================================================
    # CARGA DE ESTADO CONVERSACIONAL
    # =====================================================
    state = load_state(user_key)

    # =====================================================
    # RESOLUCIÓN DE EXPECTATIVA TELCEL
    # =====================================================
    if state.awaiting_slot == "telcel_subdomain":
        telcel_agent = TelcelAgent(
            user_message=user_message,
            context=state.slots,
            intent="telcel",
        )

        result = telcel_agent.handle()
        state.awaiting_slot = None
        save_state(user_key, state)

        return jsonify(result), 200

    # =====================================================
    # RESOLUCIÓN DE SLOT PENDIENTE (PAÍS)
    # =====================================================
    # =====================================================
    # =====================================================
# 🔀 REDIRECCIÓN DE DOMINIO: Claro → Telcel
# =====================================================
    if state.awaiting_slot == "pais" and state.intent == "claro":

        # Partimos siempre de la intención original
        original_query = state.original_query or user_message

        # Si el usuario confirmó México, materializarlo en la query
        if re.search(r"\bm[eé]xico\b", user_message.lower()):
            original_query = f"{original_query} mexico"

        # Si redefine dominio (Claro México → Telcel)
        if is_telcel_intent(user_message, action=action):
            # Abortamos flujo Claro
            state.awaiting_slot = None
            state.intent = None
            state.original_query = None
            save_state(user_key, state)

            # Reinyectamos intención ORIGINAL (ya enriquecida)
            telcel_agent = TelcelAgent(
                user_message=original_query,
                context={},
                intent="telcel",
            )

            result = telcel_agent.handle()
            return jsonify(result), 200


    try:
        # =================================================
        # INTENT APRENDE
        # =================================================
        if is_aprende_intent(user_message, action=action):
            aprende_result = run_aprende_flow(user_message)

            top = aprende_result.get("top") or []
            candidates = aprende_result.get("candidates") or []

            if top:
                return jsonify(
                    build_aprende_iframe_response(
                        user_message=user_message,
                        top_course=top[0],
                        all_candidates=candidates
                    )
                ), 200

            return jsonify({
                "success": True,
                "response": aprende_result.get(
                    "message",
                    "No contamos con cursos relacionados con tu búsqueda."
                ),
                "aprende_ia_used": True,
                "candidates": [],
                "top": []
            }), 200
        # =================================================
        # INTENT TELCEL *(lo cambiamos de lugar para que pueda detectar claro mexico como telcel)
        # =================================================
        if is_telcel_intent(user_message, action=action):
            telcel_agent = TelcelAgent(
                user_message=user_message,
                context=state.slots,
                intent="telcel",
            )

            result = telcel_agent.handle()

            # ⛔ El agente activó continuidad conversacional
            if result.get("awaiting"):
                state.intent = "telcel"
                state.awaiting_slot = result["awaiting"]
                state.original_query = user_message
                save_state(user_key, state)

            return jsonify(result), 200

        # =================================================
        # 📡📡📡 INTENT CLARO (AGENTE + RAG POR PAÍS)
        # =================================================
        print("🧭 CONTROLLER → evaluando intent CLARO")
        print("🧾 user_message:", repr(user_message))
        print("🧠 state antes de Claro:", state.__dict__ if state else None)

        if is_claro_intent(user_message, action=action):
            print("📡📡📡 INTENT CLARO DETECTADO 📡📡📡")
            logger.info("📡 Intent Claro detectado")
            claro_agent = ClaroAgent(
                user_message=user_message,
                context=state.slots,
                intent="claro"
            )

            result = claro_agent.handle()
            print("📦 RESPUESTA ClaroAgent:", result)

            # ⛔ El agente pidió país → guardar estado conversacional
            if result.get("awaiting") == "pais":
                print("💾 CONTROLLER → guardando estado: esperando PAÍS")
                state.intent = "claro"
                state.awaiting_slot = "pais"
                state.original_query = user_message
                save_state(user_key, state)
                print("🔑 user_key:", user_key)


            print("🚀 CONTROLLER DEVOLVIENDO RESPUESTA CLARO")
            return jsonify(result), 200




        # =================================================
        # CHAT NORMAL
        # =================================================
        print("⚠️ CONTROLLER → CAYÓ EN CHAT NORMAL")

        response = run_web_chat(
            user_message=user_message,
            action=action,
            user_key=user_key,
        )
        return jsonify(response), 200

    except Exception:
        logger.exception("Error procesando solicitud")
        return jsonify({
            "success": False,
            "message": "Ocurrió un error procesando tu solicitud."
        }), 500
