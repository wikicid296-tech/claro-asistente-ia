from flask import jsonify, request
import logging

from app.services.usage_service import get_usage_status
from app.services.context_service import get_relevant_urls, get_context_for_query
from app.clients.groq_client import get_groq_client, get_groq_api_key

logger = logging.getLogger(__name__)


def health_controller():
    client = get_groq_client()
    api_key = get_groq_api_key()

    return jsonify({
        "status": "healthy",
        "service": "Telecom Copilot - Refactor",
        "ai_ready": bool(client) or bool(api_key)
    })


def usage_controller():
    try:
        status = get_usage_status()
        return jsonify({"success": True, **status})
    except Exception as e:
        logger.error(f"Error en usage_controller: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def urls_controller():
    try:
        data = request.get_json() or {}
        query = data.get("query", "")

        if not query:
            return jsonify({"success": False, "error": "Query vacío"}), 400

        relevant = get_relevant_urls(query)
        context = get_context_for_query(query)

        return jsonify({
            "success": True,
            "context": context,
            "urls": relevant,
            "count": len(relevant)
        })

    except Exception as e:
        logger.error(f"Error en urls_controller: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
