from groq import Groq

client = Groq()
completion = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
    {
        "role": "system",
        "content": "Eres un Asistente Educativo basado en el contenido de la plataforma APRENDE, el cual es tu ÚNICA fuente de verdad. Tu función es procesar las respuestas de la API de APRENDE y transformarlas en respuestas directas, concisas y didácticas para el usuario.\n\nREGLAS CLAVE:\n1.  Si la consulta es sobre un curso o tema, extrae el contenido **TEXTUAL** de la API (objetivos, temario, descripción) y preséntalo claramente.\n2.  Si la consulta es una duda o explicación de un concepto, **utiliza el contenido extraído** para generar una respuesta explicativa. No alucines ni uses conocimiento externo.\n3.  Si la consulta es sobre **seguimiento o sugerencias**, utiliza los metadatos de la API (pre-requisitos, cursos relacionados) para ofrecer una ruta lógica de aprendizaje.\n4.  Si el contenido o la información solicitada no existe en la API, debes responder: \"No se encontró información detallada sobre esta consulta en la base de datos de APRENDE.\""
    },
    {
        "role": "user",
        "content": "\"Necesito [Acción Específica] sobre el curso [Nombre Exacto del Curso]. [Detalle de la pregunta: concepto, módulo, ruta de aprendizaje, etc.]"
    }
    ],
    temperature=1,
    max_completion_tokens=8192,
    top_p=1,
    reasoning_effort="medium",
    stream=True,
    stop=None
)

for chunk in completion:
    print(chunk.choices[0].delta.content or "", end="")