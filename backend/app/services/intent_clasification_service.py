import json
import logging
import re
from typing import Dict
from app.services.groq_service import run_groq_completion, get_groq_api_key

logger = logging.getLogger(__name__)
api_key = get_groq_api_key()

# 🧠 SYSTEM PROMPT (ULTRA SIMPLIFICADO)
# Solo existen 3 caminos posibles. Todo lo que no sea tarea, es chat.
INTENT_PROMPT = """
Eres el clasificador de intenciones de un asistente virtual.
Tu única misión es decidir si el usuario quiere GESTIONAR UNA TAREA o simplemente CONVERSAR.

### CATEGORÍAS PERMITIDAS (macro_intent):
Solo puedes responder con una de estas 3 opciones:

1. "task": El usuario quiere CREAR, AGENDAR o GUARDAR algo.
   - task_type="calendar": Si hay fecha/hora explícita ("reunión mañana a las 5").
   - task_type="reminder": Si es un recordatorio vago o sin hora ("recuérdame comprar pan").
   - task_type="note": Si quiere guardar texto o listas ("anota esto", "lista del súper").

2. "task_query": El usuario pregunta qué tiene agendado.
   - Ejemplos: "¿Qué tengo hoy?", "Ver mis recordatorios", "Muéstrame la agenda".

3. "chat": TODO LO DEMÁS.
   - Si pregunta por el clima, noticias, información general -> "chat".
   - Si saluda, agradece o conversa -> "chat".
   - Si pide ayuda o instrucciones -> "chat".

### FORMATO DE RESPUESTA:
Responde SOLO con este JSON válido (sin explicaciones):
{
    "macro_intent": "task | task_query | chat",
    "task_type": "calendar | reminder | note | null"
}

### EJEMPLOS (Few-Shot):
User: "Agendar dentista el viernes a las 4pm"
AI: {"macro_intent": "task", "task_type": "calendar"}

User: "Recuérdame llamar a mamá"
AI: {"macro_intent": "task", "task_type": "reminder"}

User: "¿Tengo algo pendiente para hoy?"
AI: {"macro_intent": "task_query", "task_type": null}

User: "Busca quién ganó el partido ayer"
AI: {"macro_intent": "chat", "task_type": null}

User: "Hola, buenos días"
AI: {"macro_intent": "chat", "task_type": null}

User: "Explícame los planes de internet"
AI: {"macro_intent": "chat", "task_type": null}
"""

def _clean_json_string(text: str) -> str:
    """
    Limpia la respuesta del LLM eliminando bloques Markdown (```json ... ```).
    """
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(\w+)?", "", text)
        text = re.sub(r"```$", "", text)
    return text.strip()

def classify_intent(user_message: str) -> Dict:
    """
    Clasifica la intención del usuario reduciéndola estrictamente a:
    task, task_query o chat.
    """
    text = (user_message or "").strip().lower()

    # -------------------------------------------------
    # Heurísticas duras (override) para estabilizar UX
    # -------------------------------------------------
    # "recuérdame ..." => reminder siempre, incluso si trae fecha/hora
    if re.search(r"\brecuerdame\b|\brecuérdame\b", text):
        return {
            "macro_intent": "task",
            "task_type": "reminder",
        }

    # "agenda ..." / "agendar ..." / "reunión ..." => calendar
    if re.search(r"\bagenda\b|\bagendar\b|\breunion\b|\breunión\b|\bcalendario\b|\bcita\b", text):
        return {
            "macro_intent": "task",
            "task_type": "calendar",
        }

    # "anota ..." / "nota ..." => note
    if re.search(r"\banota\b|\bnota\b|\bguardar\b|\bguarda\b", text):
        return {
            "macro_intent": "task",
            "task_type": "note",
        }

    try:
        response_payload = run_groq_completion(
            messages=[
                {"role": "system", "content": INTENT_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0, # Máxima determinismo
            groq_api_key=api_key
        )

        raw_content = ""
        
        # Extracción segura del contenido dependiendo del formato de respuesta de tu cliente Groq
        if isinstance(response_payload, dict):
            if response_payload.get("json"):
                return response_payload["json"]
            raw_content = response_payload.get("content") or response_payload.get("text") or ""
        else:
            raw_content = str(response_payload)

        cleaned_json = _clean_json_string(raw_content)
        parsed_intent = json.loads(cleaned_json)

        # Validación extra: Si el LLM alucina una categoría prohibida, forzamos 'chat'
        if parsed_intent.get("macro_intent") not in ["task", "task_query", "chat"]:
            logger.warning(f"⚠️ Intent desconocido '{parsed_intent.get('macro_intent')}' corregido a 'chat'")
            parsed_intent["macro_intent"] = "chat"
            parsed_intent["task_type"] = None

        return parsed_intent

    except Exception as e:
        logger.error(f"❌ Error crítico en classify_intent: {e}")
        # Fallback seguro
        return {
            "macro_intent": "chat",
            "task_type": None,
        }