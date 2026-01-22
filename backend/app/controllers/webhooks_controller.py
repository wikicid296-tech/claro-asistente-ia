import logging
from flask import request
from twilio.twiml.messaging_response import MessagingResponse

from app.services.cerebro_service import procesar_chat_web

logger = logging.getLogger(__name__)


# -------------------------------------------------
# Helpers generales
# -------------------------------------------------

def strip_markdown(text: str) -> str:
    if not text:
        return text

    return (
        text.replace("**", "")
            .replace("__", "")
            .replace("\n\n", "\n")
            .strip()
    )


# -------------------------------------------------
# Aprende – formatos por canal
# -------------------------------------------------

def format_aprende_for_sms(result: dict) -> str:
    """
    SMS-safe para Aprende (MX):
    - Sin URLs
    - Hasta 5 cursos
    - Instrucción de búsqueda por título o ID
    """
    candidates = result.get("candidates") or result.get("top") or []

    if not candidates:
        return (
            "Cursos disponibles en Aprende.org.\n"
            "Busca por tema o palabra clave en aprende.org."
        )

    lines = ["Cursos recomendados (Aprende.org):", ""]

    for idx, course in enumerate(candidates[:5], start=1):
        name = course.get("courseName", "Curso")
        cid = course.get("courseId", "")
        lines.append(f"{idx}. {name}")
        url = f"https://aprende.org/cursos/{cid}" if cid else "https://aprende.org"
        #if cid:
            #lines.append(f"   ID: {cid}")
        lines.append(f"visita: {url}")
        lines.append("")

    lines.append("Busca el curso por título o ID en aprende.org")

    return "\n".join(lines).strip()


def format_aprende_for_channel(result: dict) -> str:
    """
    WhatsApp / RCS:
    texto plano, informativo, con URLs permitidas
    """
    lines = []
    candidates = result.get("candidates") or result.get("top") or []

    if not candidates:
        return "Consulta cursos disponibles en aprende.org."

    lines.append("Cursos recomendados:")

    for idx, course in enumerate(candidates[:5], start=1):
        name = course.get("courseName", "Curso")
        cid = course.get("courseId", "")
        url = f"https://aprende.org/cursos/{cid}" if cid else "https://aprende.org"

        lines.append(f"{idx}. {name}")
        lines.append(url)
        lines.append("")

    return "\n".join(lines).strip()


# -------------------------------------------------
# Builder principal por canal
# -------------------------------------------------

def build_channel_message(result: dict, channel_name: str) -> str:
    # ---- APRENDE ----
    if result.get("aprende_ia_used"):
        if channel_name == "sms":
            return format_aprende_for_sms(result)
        return format_aprende_for_channel(result)

    # ---- DEFAULT ----
    text = strip_markdown(result.get("response", ""))

    # SMS: evitar meta / disclaimers
    if channel_name == "sms":
        # protección extra: nunca URLs en SMS
        #text = text.replace("http://", "").replace("https://", "")
        # fallback informativo si queda vacío
        if not text.strip():
            return "Puedo ayudarte con cursos, información y servicios. Escribe tu consulta."

    return text


# -------------------------------------------------
# Controllers
# -------------------------------------------------

def whatsapp_controller():
    return _generic_channel_controller(channel_name="whatsapp")


def sms_controller():
    return _generic_channel_controller(channel_name="sms")


def rcs_controller():
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


        if channel_name in ["whatsapp", "sms"] and incoming_msg.lower() in ["reiniciar", "reset", "empezar de nuevo"]:
            from app.states.conversationStore import clear_state, save_state, ConversationState
                # Borra estado anterior
            clear_state(from_number)
            state = ConversationState()
            state.slots["_reset"] = "true"
                # Crear estado limpio explícito (opcional pero más seguro)
            save_state(from_number, state)

            resp.message("✅ Conversación reiniciada. ¿En qué puedo ayudarte hoy?")
            return str(resp), 200, {"Content-Type": "text/xml"}




        result = procesar_chat_web(
            user_message=incoming_msg,
            action="chat",
            user_key=from_number,
        )

        message_text = build_channel_message(result, channel_name)

        if not message_text:
            message_text = (
                "Puedo ayudarte con cursos, información y servicios. "
                "Escribe el tema que te interesa."
            )

        resp.message(message_text)
        return str(resp), 200, {"Content-Type": "text/xml"}

    except Exception as e:
        logger.error(f"Error en {channel_name}_controller", exc_info=True)
        resp = MessagingResponse()
        resp.message("Ocurrió un error. Intenta nuevamente.")
        return str(resp), 200, {"Content-Type": "text/xml"}


def rcs_status_controller():
    try:
        logger.info(
            "RCS Status: sid=%s status=%s error=%s",
            request.values.get("MessageSid"),
            request.values.get("MessageStatus"),
            request.values.get("ErrorCode"),
        )
        return "", 200
    except Exception:
        logger.exception("Error en rcs_status_controller")
        return "", 200
