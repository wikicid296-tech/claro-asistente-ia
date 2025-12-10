import logging
import os
from typing import Optional, Union, Any

from app.config import settings

logger = logging.getLogger(__name__)

# Mantendremos el patrón que ya usas:
# - client real de Groq
# - o string "api_fallback"
GroqClientType = Union[Any, str, None]

_client: Optional[GroqClientType] = None


def build_groq_client() -> GroqClientType:
    """
    Inicializa el cliente de Groq.
    Retorna:
      - instancia Groq si está OK
      - "api_fallback" si hay incompatibilidad de SDK (caso proxies)
      - None si no hay key o falla fatal
    """
    if not settings.GROQ_API_KEY:
        logger.error("GROQ_API_KEY no configurada")
        return None

    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        logger.info("Cliente Groq inicializado correctamente")
        return client

    except TypeError as e:
        if "proxies" in str(e):
            logger.warning("Versión incompatible de Groq, usando fallback directo a API")
            return "api_fallback"
        logger.error(f"Error inicializando Groq (TypeError): {e}")
        return None

    except Exception as e:
        logger.error(f"Error inicializando Groq: {e}")
        return None


def get_groq_client() -> GroqClientType:
    """
    Getter singleton para evitar reinstanciar en cada request.
    """
    global _client
    if _client is None:
        _client = build_groq_client()
    return _client

def get_groq_api_key() -> Optional[str]:
    return os.getenv("GROQ_API_KEY")