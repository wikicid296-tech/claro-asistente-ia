import logging
from flask import request
from twilio.twiml.messaging_response import MessagingResponse

from app.services.cerebro_service import procesar_chat_web

logger = logging.getLogger(__name__)


# -------------------------------
# Helpers locales (urgente, simple)
# -------------------------------

def strip_markdown(text: str) -> str:
    """
    Limpieza mínima y segura:
    - quita ** __
    - colapsa saltos
    """
    if not text:
        return text

    text = text.replace("**", "")
    text = text.replace("__", "")
    text = text.replace("\n\n", "\n")
    return text.strip()


def format_aprende_for_channel(result: dict) -> str:
    """
    Representación textual plana de Aprende
    """
    lines = []

    top = (result.get("top") or [])
    candidates = (result.get("candidates") or [])

    if top:
        course = top[0]
        name = course.get("courseName", "Curso recomendado")
        cid = course.get("courseId", "")
        url = f"https://aprende.org/cursos/{cid}" if cid else "https://aprende.org"

        lines.append("Curso recomendado:")
        lines.append(name)
        lines.append(url)

    if len(candidates) > 1:
        lines.append("")
        lines.append("Otros cursos:")
        for c in candidates[1:4]:
            cname = c.get("courseName", "Curso")
            cid = c.get("courseId", "")
            url = f"https://aprende.org/cursos/{cid}" if cid else "https://aprende.org"
            lines.append(f"- {cname}: {url}")

    return "\n".join(lines).strip()


def build_channel_message(result: dict) -> str:
    """
    Decide cómo representar la respuesta del cerebro
    para canales (SMS / WhatsApp / RCS).
    """
    # Caso Aprende
    if result.get("aprende_ia_used"):
        return format_aprende_for_channel(result)

    # Default: texto plano sin markdown
    return strip_markdown(result.get("response", ""))


# -------------------------------
# Controllers
# -------------------------------

def whatsapp_controller():
    return _generic_channel_controller(channel_name="whatsapp")


def sms_controller():
    return _generic_channel_controller(channel_name="sms")


def rcs_controller():
    # GET de verificación
    if request.method == "GET":
        return "RCS Webhook activo", 200

    return _generic_channel_controller(channel_name="rcs")


def _generic_channel_controller(channel_name: str):
    try:
        incoming_msg = (request.values.get("Body", "") or "").strip()
        from_number = request.values.get("From", "")

        resp = MessagingResponse()

        if not incoming_msg:
            resp.message("Por favor envía un mensaje válido.")
            return str(resp), 200, {"Content-Type": "text/xml"}

        # Llamamos al MISMO cerebro que la web
        result = procesar_chat_web(
            user_message=incoming_msg,
            action="chat",
            user_key=from_number,
        )

        message_text = build_channel_message(result)

        if not message_text:
            message_text = "No pude generar una respuesta. Intenta reformular tu mensaje."

        resp.message(message_text)
        return str(resp), 200, {"Content-Type": "text/xml"}

    except Exception as e:
        logger.error(f"Error en {channel_name}_controller: {e}", exc_info=True)
        resp = MessagingResponse()
        resp.message("Ocurrió un error. Intenta nuevamente.")
        return str(resp), 200, {"Content-Type": "text/xml"}


def rcs_status_controller():
    try:
        message_sid = request.values.get("MessageSid")
        message_status = request.values.get("MessageStatus")
        error_code = request.values.get("ErrorCode")

        logger.info(
            f"RCS Status: sid={message_sid} status={message_status} error={error_code}"
        )
        return "", 200
    except Exception as e:
        logger.error(f"Error en rcs_status_controller: {e}")
        return "", 200
