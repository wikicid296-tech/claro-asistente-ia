import requests
from flask import Flask, jsonify

app = Flask(__name__)

API_BASE_URL = "https://besvc.capacitateparaelempleo.org/api"
API_USER = "floresed@hitss.com"
API_PASS = "oBr5_Pc7SyK$"

def autenticar():
    url_login = f"{API_BASE_URL}/Accounts/login"
    payload = {
        "email": API_USER,
        "password": API_PASS
    }

    try:
        response = requests.post(url_login, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("token") 
    except requests.exceptions.RequestException as err:
        print(f"Error de autenticación: {err}")
        return None

@app.route('/api/recursos', methods=['GET'])
def obtener_recursos():
    """
    Ruta GET: Obtiene los recursos de video del curso desde el API Resources Aprende.
    """
    token = autenticar()
    if not token:
        return jsonify({
            "status": "error",
            "mensaje": "No se pudo autenticar con el API externo."
        }), 500

    url_recursos = f"{API_BASE_URL}/Resources/getResourcesVideoAMX"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:
        response = requests.get(url_recursos, headers=headers, timeout=10)
        response.raise_for_status()

        datos_api = response.json()
        return jsonify({
            "status": "success",
            "metodo": "GET",
            "origen": "Resources Aprende",
            "recursos": datos_api
        }), 200

    except requests.exceptions.HTTPError as err_h:
        return jsonify({
            "status": "error",
            "metodo": "GET",
            "mensaje": f"Error HTTP: {err_h}. Código: {response.status_code}"
        }), response.status_code

    except requests.exceptions.RequestException as err:
        return jsonify({
            "status": "error",
            "metodo": "GET",
            "mensaje": f"Error al conectar con la API: {err}"
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
