import json
from app.services.groq_service import get_groq_client
FRESHNESS_CHECK_PROMPT = """
Analiza la siguiente pregunta del usuario.

Determina si un modelo de lenguaje con fecha de corte en diciembre de 2023
puede responder de forma correcta y suficiente SIN usar información actualizada.

Responde EXCLUSIVAMENTE en JSON con este esquema exacto:

{{
  "has_sufficient_knowledge": true | false,
  "reason": "explicación breve"
}}

Criterios:
- Si la información es cambiante, reciente o depende del estado actual → false
- Si es conocimiento estable, histórico o atemporal → true

Pregunta:
"{user_message}"
"""



def llm_can_answer_with_cutoff(user_message: str) -> bool:
    client = get_groq_client()

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": FRESHNESS_CHECK_PROMPT.format(user_message=user_message)}
        ],
        temperature=0.0,
        max_tokens=120,
    )

    content = response.choices[0].message.content
    if content is None:
        return True
    
    content = content.strip()

    try:
        data = json.loads(content)
        return bool(data.get("has_sufficient_knowledge", True))
    except Exception:
        # Fail-safe: si el parseo falla, asumimos que SÍ puede responder
        return True
