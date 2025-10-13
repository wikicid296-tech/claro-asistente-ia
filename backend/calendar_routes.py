from flask import Blueprint, request, jsonify, send_file
from calendar_ics import crear_invitacion_ics
import io
import logging

# Configurar logging
logger = logging.getLogger(__name__)

# Crear Blueprint para las rutas de calendario
calendar_bp = Blueprint('calendar', __name__, url_prefix='/calendar')


@calendar_bp.route('/create-event', methods=['POST'])
def create_event():
    """
    Crea un archivo .ics y lo retorna para descarga.
    
    Recibe JSON:
    {
        "title": "Reunión",
        "description": "Descripción del evento",
        "location": "Oficina",
        "date": "2025-10-15",
        "time": "10:00",
        "duration": 1
    }
    
    Retorna: Archivo .ics para descargar
    """
    try:
        # Obtener datos del request
        data = request.get_json()
        
        # Validar datos requeridos
        required_fields = ['title', 'date', 'time']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    "success": False,
                    "error": f"Campo requerido faltante: {field}"
                }), 400
        
        # Extraer datos con valores por defecto
        titulo = data.get('title')
        descripcion = data.get('description', 'Evento creado desde Claro Assistant')
        ubicacion = data.get('location', 'Sin ubicación especificada')
        fecha = data.get('date')
        hora = data.get('time')
        duracion = int(data.get('duration', 1))
        
        logger.info(f"📅 Creando evento: {titulo} - {fecha} {hora}")
        
        # Generar contenido del archivo .ics
        contenido_ics = crear_invitacion_ics(
            titulo=titulo,
            descripcion=descripcion,
            ubicacion=ubicacion,
            fecha=fecha,
            hora=hora,
            duracion_horas=duracion
        )
        
        # Crear un buffer en memoria con el contenido
        buffer = io.BytesIO()
        buffer.write(contenido_ics.encode('utf-8'))
        buffer.seek(0)
        
        # Generar nombre de archivo
        filename = f"evento_{fecha.replace('-', '')}_{hora.replace(':', '')}.ics"
        
        logger.info(f"✅ Archivo .ics generado: {filename}")
        
        # Retornar archivo para descarga
        return send_file(
            buffer,
            mimetype='text/calendar',
            as_attachment=True,
            download_name=filename
        )
        
    except ValueError as e:
        logger.error(f"❌ Error de validación: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Error en los datos: {str(e)}"
        }), 400
        
    except Exception as e:
        logger.error(f"❌ Error al crear evento: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Error interno al generar el evento"
        }), 500


@calendar_bp.route('/test', methods=['GET'])
def test_calendar():
    """
    Endpoint de prueba para verificar que el módulo funciona.
    """
    return jsonify({
        "success": True,
        "message": "Módulo de calendario funcionando correctamente",
        "endpoints": {
            "create_event": "/calendar/create-event (POST)"
        }
    })