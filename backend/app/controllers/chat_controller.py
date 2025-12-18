import logging
from typing import Any, Dict, List
from flask import jsonify, request
import os
from app.controllers._request_utils import get_user_key_from_request
from app.services.usage_service import is_usage_blocked, get_usage_status
from app.services.chat_orchestrator_service import run_web_chat
from app.services.content_safety_service import check_content_safety

from app.services.prompt_service import is_aprende_intent, is_telcel_intent
from app.services.aprende_search_service import run_aprende_flow
from dotenv import load_dotenv
from app.services.telcel_rag_service import TelcelRAGService
from app.services.response_synthesis_service import synthesize_answer
from app.services.groq_service import get_groq_client, get_groq_api_key
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
    Aplica content safety global y enruta por intent.
    """

    data = request.get_json(force=True, silent=True) or {}
    user_message = (data.get("message") or "").strip()
    action = data.get("action", "busqueda")
    user_key = data.get("user_key")

    print("📥 INPUT RECIBIDO:", data)

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
        print("🛡️ RESULTADO CONTENT SAFETY:", safety)
    except Exception:
        logger.exception("Error ejecutando content safety")
        safety = {"flagged": False}

    if safety.get("flagged"):
        print("⛔ MENSAJE BLOQUEADO POR CONTENT SAFETY")
        return jsonify({
            "success": False,
            "type": "blocked",
            "message": "No puedo ayudar con este tipo de contenido."
        }), 200

    # =====================================================
    # ROUTING POR INTENT
    # =====================================================
    try:
        # =================================================
        # INTENT APRENDE
        # =================================================
        if is_aprende_intent(user_message, action=action):
            print("🎓🎓🎓 INTENT APRENDE DETECTADO 🎓🎓🎓")
            logger.info("🎓 Intent Aprende detectado")

            aprende_result = run_aprende_flow(user_message)

            print("📦 RESPUESTA APRENDE:", aprende_result)

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
        # 🔥🔥🔥 INTENT TELCEL (RAG + GROQ)
        # =================================================
        MONGO_URI = os.getenv("MONGO_URI")
        if not MONGO_URI:
           raise RuntimeError("MONGO_URI no está configurada en el entorno")
        if is_telcel_intent(user_message, action=action):
            print("📱📱📱 INTENT TELCEL DETECTADO 📱📱📱")
            logger.info("📱 Intent Telcel detectado")

            groq_client = get_groq_client()
            groq_api_key = get_groq_api_key()

            telcel_service = TelcelRAGService(
                mongo_uri=MONGO_URI,
                db_name="telcel_rag",
                collection_name="embeddings"
            )

            print("🔍 Ejecutando búsqueda semántica en Mongo (Telcel)")
            raw_results = telcel_service.search(user_message)

            print(f"📊 RESULTADOS CRUDOS TELCEL ({len(raw_results)} docs):")
            for r in raw_results:
                print("➡️", r.get("titulo"), "| score:", r.get("score"))

            synthesized = synthesize_answer(
                user_question=user_message,
                documents=raw_results,
                domain_name="Telcel",
                groq_client=groq_client,
                groq_api_key=groq_api_key
            )

            print("🧠 RESPUESTA SINTETIZADA (GROQ):", synthesized)

            return jsonify({
                "success": True,
                "action": "telcel",
                "context": "📱 Información oficial de Telcel",
                "context_reset": False,
                "memory_used": 0,
                "response": synthesized["response"],
                "relevant_urls": synthesized["relevant_urls"]
            }), 200

        # =================================================
        # CHAT NORMAL
        # =================================================
        print("💬💬💬 FLUJO CHAT NORMAL 💬💬💬")

        response = run_web_chat(
            user_message=user_message,
            action=action,
            user_key=user_key
        )

        print("🤖 RESPUESTA CHAT NORMAL:", response)
        return jsonify(response), 200

    except Exception:
        logger.exception("Error procesando solicitud")
        print("🔥🔥🔥 EXCEPCIÓN NO CONTROLADA EN chat_controller 🔥🔥🔥")
        return jsonify({
            "success": False,
            "message": "Ocurrió un error procesando tu solicitud."
        }), 500
