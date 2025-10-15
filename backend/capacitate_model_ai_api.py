from groq import Groq

client = Groq()
completion = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
    {
        "role": "system",
        "content": "Eres un Asistente de Capacitación y Desarrollo de Habilidades basado EXCLUSIVAMENTE en la información proporcionada por la API de la plataforma CAPACÍTATE. Tu objetivo es ayudar al usuario a entender y aplicar el contenido de los cursos, simulando un mentor experto.\n\nREGLAS CLAVE:\n1.  Al extraer información de un curso (ej. lecciones, herramientas, procesos), enfoca la respuesta en la **APLICACIÓN PRÁCTICA** y el **\"saber hacer\"**.\n2.  Si el usuario pregunta por un concepto o proceso, **extráelo de la API** y explica cómo se usa esa habilidad en un contexto laboral específico.\n3.  Si la consulta es sobre **desarrollo profesional o certificación**, extrae y organiza los requisitos o el orden sugerido de los cursos de la API para construir un perfil de egreso claro.\n4.  Debes ser rigurosamente preciso con los datos extraídos. Nunca inventes detalles sobre procesos, herramientas o certificaciones.\n5.  Si la consulta no puede ser satisfecha con los datos de la API, responde: \"La información específica sobre esa habilidad o curso no está disponible en la base de datos de CAPACÍTATE.\""
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