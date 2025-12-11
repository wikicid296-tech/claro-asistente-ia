import logging
from typing import Any, Dict, List
from flask import jsonify, request

from app.controllers._request_utils import get_user_key_from_request
from app.services.usage_service import is_usage_blocked, get_usage_status
from app.services.chat_orchestrator_service import run_web_chat

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
            response_text += f"**{course_name}** (ID: {course_id})\n\n"
            
            if len(all_candidates) > 1:
                response_text += f"**También encontré {len(all_candidates) - 1} cursos más:**\n"
                for i, candidate in enumerate(all_candidates[1:4], 2):  # Mostrar max 3 adicionales
                    cand_name = candidate.get('courseName', 'Curso sin nombre')
                    cand_id = candidate.get('courseId', '')
                    response_text += f"{i}. **{cand_name}** (ID: {cand_id})\n"
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
    try:
        data = request.get_json() or {}

        user_message = data.get("message", "")
        action = (data.get("action", "") or "").lower().strip()
        
        # 🆕 OBTENER USER_KEY (importante para memoria)
        user_key = get_user_key_from_request()

        if not user_message:
            return jsonify({"success": False, "error": "Mensaje vacío"}), 400

        if is_usage_blocked():
            status = get_usage_status()
            return jsonify({
                "success": False,
                "error": "Límite mensual alcanzado",
                "usage": status,
            }), 429

        # 🔹 Nueva lógica: combinar modo del front + intent por texto
        use_aprende = False

        # A) Si el front está explícitamente en modo "aprende", lo respetamos SIEMPRE
        if action == "aprende":
            use_aprende = True

        # B) Si no está en modo aprende, pero el texto tiene el intent Aprende
        elif is_aprende_intent(user_message):
            use_aprende = True

        if use_aprende:
            logger.info("Modo/Intent Aprende activo → ejecutando run_aprende_flow()")
            aprende_result = run_aprende_flow(user_message, k=5, fetch_top_n=1)
            
            candidates = aprende_result.get("candidates", [])
            top_courses = aprende_result.get("top", [])
            
            if candidates and top_courses:
                top_course = top_courses[0]
                response = build_aprende_iframe_response(user_message, top_course, candidates)
                return jsonify(response)
            else:
                return jsonify({
                    "success": True,
                    "response": f"😕 No encontré cursos relacionados con '{user_message}'. ¿Podrías intentar con otras palabras clave?",
                    "aprende_ia_used": False,
                    "context": "ℹ️ Asistente general disponible"
                })

        # 🔹 Flujo normal (no Aprende) - PASAR user_key
        result = run_web_chat(
            user_message=user_message,
            action=action or "busqueda",
            user_key=user_key,  # 🆕 PASAR EL USER_KEY AQUÍ
        )

        return jsonify({"success": True, **result})

    except Exception as e:
        logger.error(f"Error en chat_controller: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500