import logging
import re
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# ============================
# ESTRUCTURA DE MEMORIA GLOBAL
# ============================
#
# CHAT_MEMORY = {
#   user_key: {
#       "facts": {...},              # memoria persistente
#       "recent": [...],             # ventana conversacional
#       "active_topic": "general"    # contexto suave
#   }
# }
#
CHAT_MEMORY: Dict[str, Dict[str, Any]] = {}


# ============================
# EXTRACCIÓN DE HECHOS
# ============================

NAME_REGEX = re.compile(
    r"(me llamo|mi nombre es|soy)\s+([a-zA-ZÁÉÍÓÚáéíóúñÑ]+)",
    re.IGNORECASE
)


def extract_facts(text: str) -> Dict[str, Any]:
    """
    Extrae hechos persistentes del mensaje del usuario.
    Esta función debe ser conservadora: solo guardar información explícita.
    """
    facts: Dict[str, Any] = {}
    if not text:
        return facts

    # Nombre del usuario
    match = NAME_REGEX.search(text)
    if match:
        facts["name"] = match.group(2).capitalize()

    return facts


# ============================
# CONTEXTO TEMÁTICO (SUAVE)
# ============================

def detect_main_topic(text: str) -> str:
    text_lower = (text or "").lower()

    telecom_keywords = [
        'claro', 'telcel', 'a1', 'plan', 'internet', 'telefon',
        'móvil', 'movil', 'datos', 'paquete', 'recarga', 'operador'
    ]
    education_keywords = [
        'curso', 'aprender', 'estudiar', 'educaci', 'diploma',
        'universidad', 'ingles', 'inglés', 'programa', 'capacita'
    ]
    health_keywords = [
        'salud', 'medic', 'doctor', 'enfermedad', 'tratamiento'
    ]

    def score(keywords: List[str]) -> int:
        return sum(1 for kw in keywords if kw in text_lower)

    scores = {
        "telecom": score(telecom_keywords),
        "education": score(education_keywords),
        "health": score(health_keywords),
    }

    best_topic = max(
    scores.items(),
    key=lambda item: item[1])[0]

    return best_topic if scores[best_topic] > 0 else "general"


# ============================
# INICIALIZACIÓN DE USUARIO
# ============================

def _ensure_user_memory(user_key: str) -> Dict[str, Any]:
    if user_key not in CHAT_MEMORY:
        CHAT_MEMORY[user_key] = {
            "facts": {},
            "recent": [],
            "active_topic": "general",
        }
    return CHAT_MEMORY[user_key]


# ============================
# API PÚBLICA
# ============================

def append_memory(
    user_key: str,
    role: str,
    message: str,
    max_recent: int = 6
) -> None:
    """
    Agrega un mensaje a la memoria del usuario.
    - Extrae hechos persistentes solo desde mensajes del usuario.
    - Mantiene una ventana conversacional acotada.
    - Actualiza el contexto temático sin borrar identidad.
    """
    memory = _ensure_user_memory(user_key)

    if role == "user":
        # Extraer hechos persistentes
        new_facts = extract_facts(message)
        if new_facts:
            logger.info(f"Hechos detectados para {user_key}: {new_facts}")
            memory["facts"].update(new_facts)

        # Actualizar contexto activo (soft)
        memory["active_topic"] = detect_main_topic(message)

    # Agregar a ventana conversacional
    memory["recent"].append({
        "role": role,
        "content": message
    })

    # Limitar tamaño de ventana
    memory["recent"] = memory["recent"][-max_recent:]


def get_memory_snapshot(user_key: str) -> Dict[str, Any]:
    """
    Devuelve una copia segura de la memoria del usuario.
    """
    memory = _ensure_user_memory(user_key)
    return {
        "facts": dict(memory["facts"]),
        "recent": list(memory["recent"]),
        "active_topic": memory["active_topic"],
    }


def build_prompt_messages(
    user_key: str,
    user_message: str
) -> List[Dict[str, str]]:
    """
    Construye la lista de mensajes que se enviará al LLM,
    inyectando memoria factual y ventana conversacional.
    """
    memory = _ensure_user_memory(user_key)

    messages: List[Dict[str, str]] = []

    # Inyección de memoria factual (NO conversacional)
    if memory["facts"]:
        system_memory = (
            "Información conocida y confirmada del usuario:\n"
            f"{memory['facts']}"
        )
        messages.append({
            "role": "system",
            "content": system_memory
        })

    # Ventana conversacional
    messages.extend(memory["recent"])

    # Mensaje actual
    messages.append({
        "role": "user",
        "content": user_message
    })

    return messages


def reset_conversation_window(user_key: str) -> None:
    """
    Limpia solo la ventana conversacional.
    NO borra hechos persistentes.
    """
    memory = _ensure_user_memory(user_key)
    memory["recent"] = []


def reset_all_memory(user_key: str) -> None:
    """
    Borra toda la memoria del usuario.
    Usar solo bajo acción explícita del usuario.
    """
    if user_key in CHAT_MEMORY:
        del CHAT_MEMORY[user_key]
