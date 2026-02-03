
import logging
from flask import request, jsonify

from app.controllers._request_utils import get_user_key_from_request
from app.services.cerebro_service import procesar_chat_web

logger = logging.getLogger(__name__)


def chat_controller():
    """
    Controller web para /chat.
    Delegación total de la lógica conversacional al cerebro_service.
    """

    data = request.get_json(silent=True) or {}
    macro_intent = data.get("macro_intent", None)
    task_type = data.get("task_type",None)
    user_message = data.get("message", "").strip()
    action = data.get("action", "chat")

    if not user_message:
        return jsonify({
            "success": False,
            "message": "El mensaje no puede estar vacío."
        }), 400

    user_key = get_user_key_from_request()

    try:
        result = procesar_chat_web(
            user_message=user_message,
            action=action,
            user_key=user_key,
            macro_intent=macro_intent,
            task_type=task_type,
        )
        return jsonify(result), 200

    except Exception:
        logger.exception("Error procesando chat web")
        return jsonify({
            "success": False,
            "message": "Ocurrió un error al procesar tu solicitud."
        }), 500
