# backend/app/routers/error_handlers.py
from __future__ import annotations

from flask import jsonify
from werkzeug.exceptions import HTTPException


def register_error_handlers(app):
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({
            "success": False,
            "error": "Demasiadas peticiones",
            "message": "Por favor espera unos segundos antes de enviar otro mensaje. Esto ayuda a mantener el servicio estable para todos.",
            "retry_after_seconds": 10
        }), 429

    @app.errorhandler(HTTPException)
    def http_exception_handler(e: HTTPException):
        return jsonify({
            "success": False,
            "error": e.name,
            "message": e.description,
            "status_code": e.code
        }), e.code

    @app.errorhandler(Exception)
    def unhandled_exception_handler(e: Exception):
        return jsonify({
            "success": False,
            "error": "Internal Server Error",
            "message": str(e)
        }), 500
