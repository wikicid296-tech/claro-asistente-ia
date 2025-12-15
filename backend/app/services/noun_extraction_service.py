import json
import logging
from typing import Any, Dict
import os

from app.services.groq_service import run_groq_completion, DEFAULT_MODEL

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
Eres un sistema de extracción lingüística.

Tu tarea es identificar el sustantivo principal que representa
aquello que el usuario desea aprender, cuidar, estudiar o comprender.

Reglas:
- Extrae únicamente el objeto principal (sustantivo o frase nominal).
- No expliques nada.
- No inventes.
- Si no existe un objeto claro, responde "NONE".
- Devuelve SIEMPRE un JSON válido.

Formato de salida:
{
  "main_noun": string,
  "confidence": number,
  "raw_phrase": string
}
""".strip()


def extract_main_noun(
    user_input: str,
    *,
    groq_client: Any = None,
    groq_api_key: str | None = None
) -> Dict[str, Any]:
    """
    Extrae el sustantivo núcleo semántico usando Groq LLM.
    """

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input}
    ]

    try:
        response_text = run_groq_completion(
            messages=messages,
            groq_client=groq_client,
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model=DEFAULT_MODEL,
            temperature=0,
            max_tokens=120,
            top_p=1,
            frequency_penalty=0
        )

        result = json.loads(response_text)

        # Validación mínima defensiva
        if "main_noun" not in result:
            raise ValueError("Respuesta sin main_noun")

        logger.info("Noun extraction (Groq): %s", result)
        return result

    except Exception as e:
        logger.error("Error en noun_extraction_service: %s", e)

        return {
            "main_noun": "NONE",
            "confidence": 0.0,
            "raw_phrase": ""
        }
