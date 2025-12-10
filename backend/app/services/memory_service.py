# app/services/memory_service.py
import logging
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

# Conservamos el storage simple actual
CHAT_MEMORY: Dict[str, List[str]] = {}


def detect_main_topic(text: str) -> str:
    text_lower = (text or "").lower()

    telecom_keywords = ['claro', 'telcel', 'a1', 'plan', 'internet', 'telefon', 'móvil', 'movil',
                        'datos', 'paquete', 'recarga', 'operador', 'señal']
    education_keywords = ['curso', 'aprender', 'estudiar', 'educaci', 'diploma', 'universidad',
                          'inglés', 'ingles', 'programa', 'capacita', 'aprende.org', 'clase',
                          'enseña', 'profesor', 'escuela', 'carrera', 'profesional']
    health_keywords = ['salud', 'medic', 'doctor', 'enfermedad', 'diabetes', 'presión', 'presion',
                       'nutrición', 'nutricion', 'dieta', 'ejercicio', 'hospital', 'sintoma',
                       'tratamiento', 'clikisalud', 'clinica']
    task_keywords = ['recordar', 'recuerdame', 'recuérdame', 'agenda', 'agendar', 'nota', 'anota',
                     'guardar', 'programa']

    counts = {
        'telecom': sum(1 for kw in telecom_keywords if kw in text_lower),
        'education': sum(1 for kw in education_keywords if kw in text_lower),
        'health': sum(1 for kw in health_keywords if kw in text_lower),
        'task': sum(1 for kw in task_keywords if kw in text_lower),
    }
    max_count = max(counts.values()) if counts else 0
    if max_count == 0:
        return 'general'

    for topic, count in counts.items():
        if count == max_count:
            return topic

    return 'general'


def detect_context_change(current_message: str, previous_messages: List[str]) -> bool:
    if not previous_messages:
        return False

    current_context = detect_main_topic(current_message)
    previous_contexts = [detect_main_topic(msg) for msg in previous_messages]

    if current_context and all(current_context != prev for prev in previous_contexts if prev):
        logger.info(f"Cambio de contexto detectado: {previous_contexts[-1] if previous_contexts else 'none'} → {current_context}")
        return True

    return False


def get_relevant_memory(user_key: str, current_message: str) -> List[str]:
    mem = CHAT_MEMORY.get(user_key, [])
    if not mem:
        return []

    if detect_context_change(current_message, mem):
        logger.info("Limpiando memoria anterior por cambio de contexto")
        CHAT_MEMORY[user_key] = []
        return []

    # Mantienes solo 1 mensaje previo hoy
    return mem[-1:]


def append_memory(user_key: str, message: str, max_len: int = 2) -> None:
    mem = CHAT_MEMORY.get(user_key, [])
    mem.append(message)

    if len(mem) > max_len:
        mem = mem[-max_len:]

    CHAT_MEMORY[user_key] = mem
