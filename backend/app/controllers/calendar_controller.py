# app/controllers/calendar_controller.py
import logging
from flask import Response, request

from app.services.calendar_ics import crear_invitacion_ics

logger = logging.getLogger(__name__)


def calendar_create_ics_controller():
    try:
        data = request.get_json() or {}

        titulo = data.get("title")
        descripcion = data.get("description", "")
        ubicacion = data.get("location", "")
        fecha = data.get("date")
        hora = data.get("time")
        duracion = float(data.get("duration", 1))

        if not titulo or not fecha or not hora:
            return {"error": "Faltan campos obligatorios"}, 400

        ics_content = crear_invitacion_ics(
            titulo=titulo,
            descripcion=descripcion,
            ubicacion=ubicacion,
            fecha=fecha,
            hora=hora,
            duracion_horas=duracion
        )

        return Response(
            ics_content,
            mimetype="text/calendar",
            headers={
                "Content-Disposition": "attachment; filename=evento.ics"
            }
        )

    except Exception as e:
        logger.error("Error generando ICS", exc_info=True)
        return {"error": str(e)}, 500
