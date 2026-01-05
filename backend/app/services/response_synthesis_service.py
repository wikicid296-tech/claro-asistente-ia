from typing import List, Dict
from app.services.groq_service import run_groq_completion




def synthesize_answer(
    *,
    user_question: str,
    documents: List[Dict],
    domain_name: str,
    groq_client,
    groq_api_key,
    max_chars_per_doc: int = 3000
) -> Dict[str, object]:

    # =====================================================
    # COMPORTAMIENTO GENÉRICO
    # =====================================================
    if not documents:
        return {
            "response": (
                f"No hay información suficiente en los canales oficiales de "
                f"{domain_name} para responder esta pregunta."
            ),
            "relevant_urls": []
        }

    docs_text = "\n\n".join(
        f"TÍTULO: {d.get('titulo', '')}\n"
        f"CONTENIDO:\n{d.get('texto', '')[:max_chars_per_doc]}"
        for d in documents
    )

    prompt = f"""
Eres un componente de síntesis de información institucional.

REGLAS ESTRICTAS:
- Representas exclusivamente al dominio indicado.
- SOLO puedes usar la información proporcionada en los documentos.
- NO puedes agregar, inferir o completar información.
- NO puedes usar conocimiento externo.
- NO puedes especular.
- NO menciones empresas, marcas o dominios distintos al indicado.
- Si la información no es suficiente, dilo explícitamente.

DOMINIO:
{domain_name}

PREGUNTA DEL USUARIO:
{user_question}

DOCUMENTOS:
{docs_text}

INSTRUCCIONES DE RESPUESTA:
- Redacta de forma clara, institucional y neutral.
- Resume fielmente el contenido.
- No inventes hechos.
- No cambies el significado del texto original.
"""

    answer = run_groq_completion(
        messages=[{"role": "system", "content": prompt}],
        groq_client=groq_client,
        groq_api_key=groq_api_key,
        temperature=0.0,
        max_tokens=1000
    )

    return {
        "response": answer.strip(),
        "relevant_urls": list({d.get("url") for d in documents if d.get("url")})
    }
