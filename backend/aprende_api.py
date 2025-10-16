import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

# --- CONFIGURACIÓN DE LA API EXTERNA ---
# URL de la API de prueba (jsonplaceholder)
API_BASE_URL = "https://jsonplaceholder.typicode.com" 

# --- RUTA PARA CONSUMIR API (MÉTODO GET) ---
@app.route('/datos/publicacion/<int:post_id>', methods=['GET'])
def obtener_datos(post_id):
    """
    Ruta GET: Obtiene una publicación específica de la API externa.
    Ejemplo de uso: /datos/publicacion/1
    """
    url = f"{API_BASE_URL}/posts/{post_id}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status() 
        
        datos_api = response.json()
        return jsonify({
            "status": "success",
            "metodo": "GET",
            "datos": datos_api
        }), 200

    except requests.exceptions.HTTPError as err_h:
        # Error 4xx o 5xx de la API externa
        return jsonify({
            "status": "error",
            "metodo": "GET",
            "mensaje": f"Error HTTP de la API: {err_h}. Código: {response.status_code}"
        }), response.status_code
    
    except requests.exceptions.RequestException as err:
        # Errores de conexión, timeout, etc.
        return jsonify({
            "status": "error",
            "metodo": "GET",
            "mensaje": f"Error al conectar con la API: {err}"
        }), 500

# --- RUTA PARA CONSUMIR API (MÉTODO POST) ---
@app.route('/datos/crear-publicacion', methods=['POST'])
def crear_datos():
    """
    Ruta POST: Envía datos JSON para crear un nuevo recurso en la API externa.
    """
    url = f"{API_BASE_URL}/posts"
    datos_a_enviar = request.get_json()

    if not datos_a_enviar:
        return jsonify({
            "status": "error",
            "metodo": "POST",
            "mensaje": "Se requiere un cuerpo JSON en la solicitud."
        }), 400

    try:
        # El parámetro 'json=' automáticamente serializa el diccionario y establece el header Content-Type
        response = requests.post(
            url, 
            json=datos_a_enviar, 
            timeout=10
        )
        response.raise_for_status() 

        datos_api = response.json()
        return jsonify({
            "status": "success",
            "metodo": "POST",
            "mensaje": "Recurso creado exitosamente en la API.",
            "respuesta_api": datos_api
        }), response.status_code # Normalmente 201 (Created)

    except requests.exceptions.HTTPError as err_h:
        # Error 4xx o 5xx de la API externa
        return jsonify({
            "status": "error",
            "metodo": "POST",
            "mensaje": f"Error HTTP de la API: {err_h}. Código: {response.status_code}",
            "detalle": response.text 
        }), response.status_code
    
    except requests.exceptions.RequestException as err:
        # Errores de conexión, timeout, etc.
        return jsonify({
            "status": "error",
            "metodo": "POST",
            "mensaje": f"Error al conectar con la API: {err}"
        }), 500

if __name__ == '__main__':
    app.run(debug=True)

