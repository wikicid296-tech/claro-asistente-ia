from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from .config import settings


# Extensión CORS
cors = CORS()


# Extensión Rate Limiter
# Se inicializa con init_app(app) desde create_app()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=list(settings.DEFAULT_LIMITS),
    storage_uri=settings.RATE_LIMIT_STORAGE_URI
)


def register_error_handlers(app):
    """
    Mantener handlers HTTP globales fuera del server principal.
    """
    from flask import jsonify

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({
            "success": False,
            "error": "Demasiadas peticiones",
            "message": (
                "Por favor espera unos segundos antes de enviar otro mensaje. "
                "Esto ayuda a mantener el servicio estable para todos."
            ),
            "retry_after_seconds": 10
        }), 429
