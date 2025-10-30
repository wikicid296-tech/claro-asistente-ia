from flask import Flask, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI
import os
import re

app = Flask(__name__)
load_dotenv()


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
vector_store_id = os.getenv("VECTOR_STORE_ID")

def ask_about_vector_store(client, vector_store_id, question):
    response = client.responses.create(
    model="gpt-4o-2024-11-20",
    input=[
        {
            "role": "system",
            "content": "Eres Claria un asistente experto en capacitación profesional e identificación de recursos de aprendizaje adecuados disponibles en la plataforma Aprende.org"
                    "Tu tarea es recomendar recursos y cursos útiles al usuario basándote en su pregunta, además de respoder a posibles dudas que pueda tener."
                    "siempre incluye una URL directa al recurso o curso que recomiendas, si es una duda del usuario, responde su duda y suguiere un recurso relacionado."
                    "Mantén un tono cordial, amigable y accesible. Nunca respondas con una pregunta para el usuario"
        },
        {
            "role": "user",
            "content": question
        }
    ],
    tools=[{
        "type": "file_search",
        "vector_store_ids": [vector_store_id],
        "max_num_results": 1
    }]
    )

    texto_respuesta = response.output_text.strip()
    patron_url = r'https?://[^\s\)\]\}\>]+'
    coincidencias = re.findall(patron_url, texto_respuesta)
    url_recurso = coincidencias[0] if coincidencias else ""
    resultado = {
        "respuesta": texto_respuesta,
        "url_recurso": url_recurso
    }
    return resultado

@app.route("/preguntar", methods=["POST"])
def preguntar():
    data = request.get_json()

    if not data or "pregunta" not in data:
        return jsonify({"error": "Falta el campo 'pregunta' en el cuerpo de la solicitud"}), 400

    pregunta = data["pregunta"]

    try:
        resultado = ask_about_vector_store(client, vector_store_id, pregunta)
        return jsonify(resultado)
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)




