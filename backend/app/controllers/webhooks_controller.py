import logging
from flask import request
from twilio.twiml.messaging_response import MessagingResponse

from app.controllers._async_utils import run_async
from app.clients.groq_client import get_groq_client, get_groq_api_key
from app.services.chat_orchestrator_service import run_channel_chat

logger = logging.getLogger(__name__)


def whatsapp_controller():
    try:
        incoming_msg = (request.values.get("Body", "") or "").strip()
        from_number = request.values.get("From", "")

        if not incoming_msg:
            resp = MessagingResponse()
            resp.message("Por favor envía un mensaje válido.")
            return str(resp), 200, {"Content-Type": "text/xml"}

        client = get_groq_client()
        api_key = get_groq_api_key()

        result = run_channel_chat(
            channel="whatsapp",
            user_message=incoming_msg,
            user_key=from_number,
            groq_client=client,
            groq_api_key=api_key,
            temperature=0.5,
            max_tokens=1000,
        )

        resp = MessagingResponse()
        resp.message(result["response"])
        return str(resp), 200, {"Content-Type": "text/xml"}

    except Exception as e:
        logger.error(f"Error en whatsapp_controller: {e}", exc_info=True)
        resp = MessagingResponse()
        resp.message("❌ Error. Intenta nuevamente.")
        return str(resp), 200, {"Content-Type": "text/xml"}


def sms_controller():
    try:
        incoming_msg = (request.values.get("Body", "") or "").strip()
        from_number = request.values.get("From", "")

        if not incoming_msg:
            resp = MessagingResponse()
            resp.message("Mensaje invalido")
            return str(resp), 200, {"Content-Type": "text/xml"}

        client = get_groq_client()
        api_key = get_groq_api_key()

        result = run_channel_chat(
            channel="sms",
            user_message=incoming_msg,
            user_key=from_number,
            groq_client=client,
            groq_api_key=api_key,
            temperature=0.5,
            max_tokens=1000,
        )

        resp = MessagingResponse()
        resp.message(result["response"])
        return str(resp), 200, {"Content-Type": "text/xml"}

    except Exception as e:
        logger.error(f"Error en sms_controller: {e}", exc_info=True)
        resp = MessagingResponse()
        resp.message("Error. Reintentar")
        return str(resp), 200, {"Content-Type": "text/xml"}


def rcs_controller():
    try:
        # GET para verificación
        if request.method == "GET":
            return "RCS Webhook activo", 200

        incoming_msg = ""
        from_number = ""

        if request.is_json:
            data = request.get_json() or {}
            incoming_msg = (data.get("Body", "") or "").strip()
            from_number = data.get("From", "")
        else:
            incoming_msg = (request.values.get("Body", "") or "").strip()
            from_number = request.values.get("From", "")

        if not incoming_msg:
            resp = MessagingResponse()
            resp.message("Por favor envía un mensaje válido.")
            return str(resp), 200, {"Content-Type": "text/xml"}

        client = get_groq_client()
        api_key = get_groq_api_key()

        result = run_channel_chat(
            channel="rcs",
            user_message=incoming_msg,
            user_key=from_number,
            groq_client=client,
            groq_api_key=api_key,
            temperature=0.5,
            max_tokens=1000,
        )

        resp = MessagingResponse()
        resp.message(result["response"])
        return str(resp), 200, {"Content-Type": "text/xml"}

    except Exception as e:
        logger.error(f"Error en rcs_controller: {e}", exc_info=True)
        resp = MessagingResponse()
        resp.message("❌ Error al procesar mensaje. Intenta nuevamente.")
        return str(resp), 200, {"Content-Type": "text/xml"}


def rcs_status_controller():
    # Mantener simple y sin lógica de negocio
    try:
        message_sid = request.values.get("MessageSid")
        message_status = request.values.get("MessageStatus")
        error_code = request.values.get("ErrorCode")

        logger.info(f"RCS Status: sid={message_sid} status={message_status} error={error_code}")
        return "", 200
    except Exception as e:
        logger.error(f"Error en rcs_status_controller: {e}")
        return "", 200
