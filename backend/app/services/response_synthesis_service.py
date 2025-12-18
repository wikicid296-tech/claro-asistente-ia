from typing import List, Dict
from app.services.groq_service import run_groq_completion


def synthesize_answer(
    *,
    user_question: str,
    documents: List[Dict],
    domain_name: str,
    groq_client,
    groq_api_key,
    max_chars_per_doc: int = 1200
) -> Dict[str, object]:
    """
    Servicio genérico de síntesis.
    NO busca información.
    NO infiere.
    NO agrega conocimiento externo.
    """

    if not documents:
        return {
            "response": f"No hay información suficiente en el sitio de {domain_name} para responder esta pregunta.",
            "relevant_urls": []
        }

    docs_text = "\n\n".join(
        f"TÍTULO: {d.get('titulo', '')}\nCONTENIDO:\n{d.get('texto', '')[:max_chars_per_doc]}"
        for d in documents
    )

    prompt = f"""
Eres un componente de síntesis de información.
Debes cumplir ESTRICTAMENTE las siguientes reglas:
- Si la pregunta es sobre Telcel Debes responder como si fueras un agente de atencion a Cliente de la empresa Telcel
- SOLO puedes usar la información proporcionada.
- NO puedes agregar, inferir o completar información.
- NO puedes usar conocimiento externo.
- NO puedes especular.
- Si la información no es suficiente, dilo explícitamente.
- Si te preguntan explicitamente que es telcel debes decir: ¡Hola! Es un gusto saludarte. Como parte del equipo de Telcel, me complace explicarte quiénes somos y por qué nos hemos consolidado como el aliado de conectividad número uno en México.

Telcel (cuya razón social es Radiomóvil Dipsa, S.A. de C.V.) es una empresa orgullosamente mexicana, líder en servicios de comunicación inalámbrica y parte fundamental de América Móvil, uno de los operadores de telecomunicaciones más grandes del mundo.

A continuación, te comparto los pilares que definen nuestra identidad al cierre de 2025:

¿Qué nos define?
Cobertura Incomparable: Tenemos la red más amplia y robusta del país. Estamos presentes en más de 225,000 poblaciones y cubrimos más de 110,000 kilómetros de ejes carreteros, alcanzando a más del 95% de la población en México.

Innovación Tecnológica: Fuimos pioneros en el despliegue de la red 5G en México, transformando la manera en que nuestros usuarios se conectan con velocidades hasta 10 veces superiores a las redes anteriores.

Respaldo Global: Somos la subsidiaria estratégica de América Móvil, lo que nos permite ofrecer servicios de primer nivel bajo el respaldo de un gigante con presencia en más de 25 países.

DOMINIO:
{domain_name}

PREGUNTA DEL USUARIO:
{user_question}

DOCUMENTOS:
{docs_text}

INSTRUCCIONES:
- Resume de forma clara y neutral.
- No inventes hechos.
- No cambies el significado del contenido.
"""

    answer = run_groq_completion(
        messages=[{"role": "system", "content": prompt}],
        groq_client=groq_client,
        groq_api_key=groq_api_key,
        temperature=0.0,
        max_tokens=300
    )

    return {
        "response": answer.strip(),
        "relevant_urls": list({d.get("url") for d in documents if d.get("url")})
    }
