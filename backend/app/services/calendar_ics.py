from datetime import datetime, timedelta
import uuid


DEFAULT_TIMEZONE = "America/Mexico_City"


def _parse_datetime(fecha: str, hora: str) -> datetime:
    """
    Convierte fecha (YYYY-MM-DD) y hora (HH:MM) en datetime naive.
    El timezone se maneja a nivel calendario (TZID).
    """
    try:
        return datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
    except ValueError as e:
        raise ValueError(f"Fecha u hora inválida: {e}")


def crear_invitacion_ics(
    *,
    titulo: str,
    descripcion: str = "",
    ubicacion: str = "",
    fecha: str,
    hora: str,
    duracion_horas: float = 1,
    timezone: str = DEFAULT_TIMEZONE,
) -> str:
    """
    Genera el contenido de un archivo .ics (iCalendar).

    Este service:
    - NO escribe archivos
    - NO maneja HTTP
    - NO decide UX
    """

    if not titulo:
        raise ValueError("El título del evento es obligatorio")
    if not fecha or not hora:
        raise ValueError("Fecha y hora son obligatorias")

    inicio = _parse_datetime(fecha, hora)
    fin = inicio + timedelta(minutes=int(duracion_horas * 60))

    uid = f"{uuid.uuid4()}@claria.ai"
    dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    dtstart = inicio.strftime("%Y%m%dT%H%M%S")
    dtend = fin.strftime("%Y%m%dT%H%M%S")

    ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Claria//Calendar//ES
CALSCALE:GREGORIAN
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{dtstamp}
SUMMARY:{_escape_text(titulo)}
DESCRIPTION:{_escape_text(descripcion)}
LOCATION:{_escape_text(ubicacion)}
DTSTART;TZID={timezone}:{dtstart}
DTEND;TZID={timezone}:{dtend}
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR
"""

    return ics.strip()


def _escape_text(text: str) -> str:
    """
    Escapa texto según RFC 5545.
    """
    if not text:
        return ""
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )
