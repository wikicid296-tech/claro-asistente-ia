import logging
from typing import Any, Dict, List
from flask import jsonify, request

from app.controllers._request_utils import get_user_key_from_request
from app.services.usage_service import is_usage_blocked, get_usage_status
from app.services.chat_orchestrator_service import run_web_chat
from app.services.content_safety_service import check_content_safety

from app.services.prompt_service import is_aprende_intent
from app.services.aprende_search_service import run_aprende_flow

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
    
    # 🔥 URL DEL CURSO - Esto es lo más importante
    course_url = f"https://aprende.org/cursos/{course_id}" if course_id else "https://aprende.org"
    
    # 🔥 Respuesta de texto simple
    if mejor_score >0.35:
        if all_candidates:
            response_text = f"🎓 Encontré {len(all_candidates)} cursos relacionados con '{user_message}':\n\n"
            response_text += f"**{course_name}** (Numero de curso: {course_id})\n\n"
            
            if len(all_candidates) > 1:
                response_text += f"**También encontré {len(all_candidates) - 1} cursos más:**\n"
                for i, candidate in enumerate(all_candidates[1:4], 2):  # Mostrar max 3 adicionales
                    cand_name = candidate.get('courseName', 'Curso sin nombre')
                    cand_id = candidate.get('courseId', '')
                    response_text += f"{i}. **{cand_name}** (Numero de curso: {cand_id})\n"
        else:
            response_text = f"😕 No encontré cursos relacionados con '{user_message}'. ¿Podrías intentar con otras palabras clave?"
    else:
        response_text = f"😕 No encontré cursos relacionados con '{user_message}'. ¿Podrías intentar con otras palabras clave?"
        course_url=None
    # 🔥 RESPUESTA MINIMALISTA PERO COMPLETA para el frontend
    return {
        "success": True,
        "response": response_text,
        "aprende_ia_used": True,
        "context": "🎓 ÁREA: EDUCACIÓN Y DESARROLLO PROFESIONAL (Aprende.org)",
        "context_reset": False,
        "memory_used": 0,
        "relevant_urls": [course_url],
        
        # 🔥 CAMPOS CRÍTICOS PARA EL VISOR DEL FRONTEND
        "tipo_contenido": "webpage",    # Siempre webpage para iframe
        "tipo_recurso": "curso",        # 🔥 DEBE SER 'curso' para que funcione
        "url_pdf": "",                  # Vacío - no usamos PDF
        "url_recurso": course_url,      # 🔥 URL que irá en el iframe
        "url_video": "",                # Vacío - no usamos video
        
        # Campos adicionales para compatibilidad
        "query": user_message,
        "candidates": all_candidates[:10],  # Limitar a 10 para no hacer la respuesta muy grande
        "top": [top_course]
    }


def chat_controller():
    """
    Controller principal del endpoint /chat.
    Aplica content safety global y enruta por intent (Aprende vs Chat).
    """

    data = request.get_json(force=True, silent=True) or {}
    user_message = (data.get("message") or "").strip()
    action = data.get("action", "busqueda")
    user_key = data.get("user_key")

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
        # Fail-open controlado
        safety = {"flagged": False}

    if safety.get("flagged"):
        logger.warning(
            "⛔ Input bloqueado por moderación | categories=%s",
            safety.get("categories")
        )
        return jsonify({
            "success": False,
            "type": "blocked",
            "message": "No puedo ayudar con este tipo de contenido."
        }), 200

    # =====================================================
    # ROUTING POR INTENT
    # =====================================================
    try:
        if is_aprende_intent(user_message,action=action):
            logger.info("🎓 Intent Aprende detectado")

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
        # CHAT NORMAL
        # =================================================
        response = run_web_chat(
            user_message=user_message,
            action=action,
            user_key=user_key
        )
        return jsonify(response), 200

    except Exception:
        logger.exception("Error procesando solicitud")
        return jsonify({
            "success": False,
            "message": "Ocurrió un error procesando tu solicitud."
        }), 500
