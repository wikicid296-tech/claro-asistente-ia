from typing import List, Dict
from app.services.groq_service import run_groq_completion


TELCEL_ABOUT_TEXT = """
¡Hola! Es un gusto saludarte. Como parte del equipo de Telcel,
me complace explicarte quiénes somos y por qué nos hemos consolidado
como el aliado de conectividad número uno en México.

Telcel (cuya razón social es Radiomóvil Dipsa, S.A. de C.V.)
es una empresa orgullosamente mexicana, líder en servicios de
comunicación inalámbrica y parte del grupo América Móvil,
uno de los operadores de telecomunicaciones más grandes del mundo.

¿Qué nos define?

Cobertura incomparable:
Contamos con la red móvil más amplia y robusta de México,
con presencia en más de 225,000 poblaciones y cobertura en
más de 110,000 kilómetros de carreteras, alcanzando a más del
95% de la población.

Innovación tecnológica:
Fuimos pioneros en el despliegue de la red 5G en México,
ofreciendo velocidades superiores y nuevas experiencias
de conectividad.

Respaldo global:
Formamos parte de América Móvil, lo que nos permite operar
con estándares internacionales y ofrecer servicios de alta calidad.
""".strip()


def synthesize_answer(
    *,
    user_question: str,
    documents: List[Dict],
    domain_name: str,
    groq_client,
    groq_api_key,
    max_chars_per_doc: int = 3000
) -> Dict[str, object]:
    """
    Servicio genérico de síntesis.

    Telcel es un caso legacy:
    - Mientras no tenga agente propio, su 'about' vive aquí.
    - Ningún otro dominio tiene lógica especial en este nivel.
    """

    normalized_question = user_question.strip().lower()

    # =====================================================
    # CASO LEGACY TELCEL (CONTROLADO)
    # =====================================================
    if domain_name.lower() == "telcel" and normalized_question in {
        "que es telcel",
        "qué es telcel",
        "informacion sobre telcel",
        "información sobre telcel",
    }:
        return {
            "response": TELCEL_ABOUT_TEXT,
            "relevant_urls": []
        }

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
