from typing import Dict, Any

from app.services.datetime_normalizer_service import normalize_datetime_from_text

def analyze_task(*, text: str, task_type: str) -> Dict[str, Any]:
    """
    Analiza un texto de tarea y extrae señales estructuradas mínimas.
    """
    analysis: Dict[str, Any] = {
        "fecha": None,
        "hora": None,
        "missing_fields": [],
        "meeting_type": None,
        "location": None,  
    }

    dt = normalize_datetime_from_text(text=text)
    analysis["fecha"] = dt.get("fecha")
    analysis["hora"] = dt.get("hora")

    text_lower = text.lower()
    

    virtual_keywords = [
        'video llamada', 'videollamada', 'llamada', 'zoom', 'teams',
        'google meet', 'meet', 'virtual', 'online', 'remoto',
        'conferencia', 'conferencia virtual', 'skype', 'webex'
    ]
    
    presencial_keywords = [
        'presencial', 'en persona', 'en oficina', 'físico',
        'cara a cara', 'en el sitio', 'en la empresa',
        'sala de juntas', 'oficina', 'local'
    ]

    for keyword in virtual_keywords:
        if keyword in text_lower:
            analysis["meeting_type"] = "virtual"
            break
    
    if not analysis["meeting_type"]:
        for keyword in presencial_keywords:
            if keyword in text_lower:
                analysis["meeting_type"] = "presencial"
                analysis["location"] = "Lugar por confirmar"
                break
    

    if task_type == "calendar":
        if not analysis["fecha"] or not analysis["hora"]:
            analysis["missing_fields"].append("datetime")


        if analysis.get("meeting_type") == "virtual" and "http" not in text_lower:
            analysis["missing_fields"].append("meeting_link")

    return analysis
