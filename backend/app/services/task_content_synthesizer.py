import re


_MONTHS = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "setiembre", "octubre",
    "noviembre", "diciembre"
)

_WEEKDAYS = (
    "lunes", "martes", "miércoles", "miercoles", "jueves",
    "viernes", "sábado", "sabado", "domingo"
)

_LEADING_INSTRUCTIONS = (
    "por favor",
    "porfa",
    "favor de",
    "que",
    "quiero",
    "necesito",
    "recuerdame",
    "recuérdame",
    "recordar",
    "agenda",
    "agendar",
    "agrega",
    "agregar",
    "añade",
    "añadir",
    "programa",
    "programar",
    "crea",
    "crear",
    "haz",
    "hacer",
)


def synthesize_task_content(text: str) -> str:
    if not text:
        return ""

    t = text.strip().lower()

    # Strip leading instruction phrases (repeatable)
    changed = True
    while changed:
        changed = False
        for phrase in _LEADING_INSTRUCTIONS:
            if t.startswith(phrase + " "):
                t = t[len(phrase):].lstrip()
                changed = True
                break

    # Normalize "para" -> "de" when describing ownership/context
    t = re.sub(r"\bpara\b", "de", t)

    # Remove common date ranges / relative days
    t = re.sub(r"\b(pasado\s+mañana|pasado\s+manana)\b", " ", t)
    t = re.sub(r"\b(mañana|manana|hoy|esta\s+semana|este\s+fin\s+de\s+semana|fin\s+de\s+semana)\b", " ", t)
    t = re.sub(r"\bpr[oó]ximos?\s+\d+\s+d[ií]as\b", " ", t)

    # Remove weekdays
    t = re.sub(r"\b(" + "|".join(_WEEKDAYS) + r")\b", " ", t)

    # Remove explicit dates (YYYY-MM-DD / DD-MM-YYYY / DD/MM)
    t = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", t)
    t = re.sub(r"\b\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?\b", " ", t)
    t = re.sub(r"\b\d{1,2}\s+de\s+(" + "|".join(_MONTHS) + r")\b", " ", t)

    # Remove time phrases
    t = re.sub(r"\b(a\s+las|a\s+la|al)\s+\d{1,2}(:\d{2})?\s*(am|pm|a\.m\.|p\.m\.)?\b", " ", t)
    t = re.sub(r"\b\d{1,2}(:\d{2})?\s*(am|pm|a\.m\.|p\.m\.)\b", " ", t)
    t = re.sub(r"\bde\s+la\s+(mañana|manana|tarde|noche)\b", " ", t)

    # Remove location prepositions that add noise
    t = re.sub(r"\ben\s+(el|la|los|las)\b", " ", t)

    # Remove possessive pronouns (keep meaning short)
    t = re.sub(r"\b(mi|mis|tu|tus|su|sus|nuestro|nuestra|nuestros|nuestras)\b", " ", t)

    # Collapse spaces and trim punctuation
    t = re.sub(r"\s+", " ", t).strip(" -:,.")

    if not t:
        return text.strip()

    return t[0].upper() + t[1:]
