import logging
from typing import Optional, Any

from app.config import settings

logger = logging.getLogger(__name__)

_client: Optional[Any] = None


def build_twilio_client() -> Optional[Any]:
    """
    Inicializa Twilio si hay credenciales.
    """
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.warning("Credenciales de Twilio no configuradas")
        return None

    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        logger.info("Cliente Twilio inicializado correctamente")
        return client
    except Exception as e:
        logger.error(f"Error inicializando Twilio: {e}")
        return None


def get_twilio_client() -> Optional[Any]:
    global _client
    if _client is None:
        _client = build_twilio_client()
    return _client
