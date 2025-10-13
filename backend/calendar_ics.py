from datetime import datetime, timedelta
import uuid

def convertir_a_datetime(fecha, hora):
    """
    Convierte strings de fecha y hora a objeto datetime.
    
    Args:
        fecha (str): Fecha en formato "YYYY-MM-DD" (ej: "2025-10-15")
        hora (str): Hora en formato "HH:MM" (ej: "14:30")
    
    Returns:
        datetime: Objeto datetime combinado
    """
    try:
        # Combinar fecha y hora
        fecha_hora_str = f"{fecha} {hora}"
        return datetime.strptime(fecha_hora_str, "%Y-%m-%d %H:%M")
    except ValueError as e:
        raise ValueError(f"Error al convertir fecha/hora: {e}")


def crear_invitacion_ics(titulo, descripcion, ubicacion, fecha, hora, duracion_horas=1):
    """
    Crea el contenido de un archivo .ics con los datos de un evento.
    
    Args:
        titulo (str): Título del evento
        descripcion (str): Descripción del evento
        ubicacion (str): Ubicación del evento
        fecha (str): Fecha en formato "YYYY-MM-DD"
        hora (str): Hora en formato "HH:MM"
        duracion_horas (int): Duración del evento en horas (default: 1)
    
    Returns:
        str: Contenido del archivo .ics listo para descargar
    """
    
    # Convertir fecha y hora a datetime
    inicio = convertir_a_datetime(fecha, hora)
    fin = inicio + timedelta(hours=duracion_horas)
    
    # Generar UID único para el evento
    uid_unico = str(uuid.uuid4())
    
    # Formatear fechas para el formato .ics (UTC)
    inicio_utc = inicio.strftime('%Y%m%dT%H%M%S')
    fin_utc = fin.strftime('%Y%m%dT%H%M%S')
    dtstamp = datetime.now().strftime('%Y%m%dT%H%M%SZ')
    
    # Crear contenido del archivo .ics
    evento = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Claro Assistant//ES
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:{uid_unico}@claroassistant.com
SUMMARY:{titulo}
DESCRIPTION:{descripcion}
LOCATION:{ubicacion}
DTSTAMP:{dtstamp}
DTSTART:{inicio_utc}
DTEND:{fin_utc}
STATUS:CONFIRMED
SEQUENCE:0
END:VEVENT
END:VCALENDAR"""
    
    return evento


# ========== BLOQUE DE PRUEBA ==========
if __name__ == "__main__":
    """
    Prueba local del generador de .ics
    Ejecuta: python calendar_ics.py
    """
    print("🧪 Probando generador de archivos .ics...\n")
    
    # Datos de prueba
    titulo_prueba = "Reunión de Proyecto Claro Assistant"
    descripcion_prueba = "Revisar avances y definir próximos pasos del chatbot"
    ubicacion_prueba = "Oficina Central / Zoom"
    fecha_prueba = "2025-10-15"
    hora_prueba = "10:00"
    duracion_prueba = 1
    
    try:
        # Generar contenido .ics
        contenido_ics = crear_invitacion_ics(
            titulo=titulo_prueba,
            descripcion=descripcion_prueba,
            ubicacion=ubicacion_prueba,
            fecha=fecha_prueba,
            hora=hora_prueba,
            duracion_horas=duracion_prueba
        )
        
        # Guardar archivo de prueba
        with open("prueba_evento.ics", "w", encoding="utf-8") as f:
            f.write(contenido_ics)
        
        print("✅ Archivo de prueba creado: prueba_evento.ics")
        print(f"\n📅 Evento: {titulo_prueba}")
        print(f"📍 Lugar: {ubicacion_prueba}")
        print(f"🕐 Fecha: {fecha_prueba} a las {hora_prueba}")
        print(f"⏱️  Duración: {duracion_prueba} hora(s)")
        print("\n💡 Abre el archivo 'prueba_evento.ics' para agregarlo a tu calendario")
        
    except Exception as e:
        print(f"❌ Error en la prueba: {e}")