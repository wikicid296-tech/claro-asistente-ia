# intents/intent_resolver.py

from company_intents.telcel_intent import handle_telcel_intent


def resolve_intent(user_message: str, context: dict) -> dict:
    msg = user_message.lower()

    if "telcel" in msg:
        return handle_telcel_intent(user_message, context)

    # fallback existente
    return {
        "action": "busqueda",
        "context": "ℹ️ Asistente general disponible",
        "context_reset": True,
        "memory_used": 0,
        "relevant_urls": [],
        "response": "¿En qué puedo ayudarte?",
        "success": True
    }
