import logging
from flask import jsonify, request

from calendar_ics import crear_invitacion_ics  # si ya lo moviste a app/, ajusta import

logger = logging.getLogger(__name__)


def calendar_create_ics_controller():
    try:
        data = request.get_json() or {}

        titulo = data.get("titulo")
        descripcion = data.get("descripcion", "")
        ubicacion = data.get("ubicacion", "")
        inicio = data.get("inicio")
        fin = data.get("fin")
        timezone = data.get("timezone", "America/Mexico_City")

        if not titulo or not inicio or not fin:
            return jsonify({
                "success": False,
                "error": "Faltan campos obligatorios: titulo, inicio, fin"
            }), 400

        ics_content = crear_invitacion_ics(
            titulo=titulo,
            descripcion=descripcion,
            ubicacion=ubicacion,
            fecha=None,
            hora=None
        )

        return jsonify({
            "success": True,
            "ics": ics_content
        })

    except Exception as e:
        logger.error(f"Error en calendar_create_ics_controller: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
