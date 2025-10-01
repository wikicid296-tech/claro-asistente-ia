from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from dotenv import load_dotenv
import logging
import requests
import json

# ==================== CONFIGURACIÓN ====================
load_dotenv()

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PORT = int(os.getenv("PORT", 10000))

# Inicializar cliente Groq - Versión compatible
try:
    if GROQ_API_KEY:
        # Para versiones más recientes de groq
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        logger.info("✅ Cliente Groq inicializado correctamente")
    else:
        logger.error("❌ GROQ_API_KEY no configurada en variables de entorno")
        client = None
except TypeError as e:
    if "proxies" in str(e):
        logger.warning("⚠️  Versión incompatible de Groq, usando fallback directo a API")
        client = "api_fallback"
    else:
        logger.error(f"❌ Error inicializando Groq: {str(e)}")
        client = None
except Exception as e:
    logger.error(f"❌ Error inicializando Groq: {str(e)}")
    client = None

# ==================== URLs DE CONTENIDO ====================
URLS = {
    "claro": {
        "argentina": [
            "https://www.claro.com.ar/personas",
            "https://www.claro.com.ar/negocios",
            "https://www.claro.com.ar/empresas"
        ],
        "peru": [
            "https://www.claro.com.pe/personas/",
            "https://www.claro.com.pe/empresas/"
        ],
        "chile": [
            "https://www.clarochile.cl/personas/",
            "https://www.clarochile.cl/negocios/",
            "https://www.clarochile.cl/empresas/"
        ],
    },
    "telcel": ["https://www.telcel.com/"],
    "a1": {
        "austria": ["https://a1.group/a1-group-and-markets/a1-in-austria/"],
        "bulgaria": ["https://a1.group/a1-group-and-markets/a1-in-bulgaria/"],
        "croacia": ["https://a1.group/a1-group-and-markets/a1-in-croatia/"],
        "bielorrusia": ["https://a1.group/a1-group-and-markets/a1-in-belarus/"],
        "serbia": ["https://a1.group/a1-group-and-markets/a1-in-serbia/"],
        "eslovenia": ["https://a1.group/a1-group-and-markets/a1-in-slovenia/"],
        "macedonia": ["https://a1.group/a1-group-and-markets/a1-in-north-macedonia/"]
    },
    "health": [
        "https://aprende.org/cuidado-salud",
        "https://aprende.org/profesionales-salud",
        "https://aprende.org/videos-salud/102382",
        "https://aprende.org/area/salud",
        "https://aprende.org/donacion-organos/1707",
        "https://aprende.org/cursos/view/100238",
    ],
    "education": [
        "https://aprendeconclaro.claro.com.sv/educacion-digital/",
        "https://www.claro.com.co/institucional/aprende-con-claro/",
        "https://www.claro.com.ni/institucional/inclusion-digital-plataforma-educativa/",
        "https://aprendeconclaro.claro.com.hn/educacion-digital/",
        "https://aprendeconclaro.claro.com.pe/educacion-digital/",
        "https://aprendeconclaro.claro.com.sv/educacion-academica/",
        "https://aprendeconclaro.claro.com.hn/educacion-academica/",
        "https://aprendeconclaro.claro.com.gt/educacion-academica/",
        "https://aprendeconclaro.claro.com.pe/educacion-academica/",
    ]
}

# ==================== SYSTEM PROMPT ====================
SYSTEM_PROMPT = """Eres un asistente especializado en servicios de telecomunicaciones, salud y educación.

CAPACIDADES:
- Telecomunicaciones: Claro (Argentina, Perú, Chile), Telcel (México), A1 (Austria, Bulgaria, etc.)
- Servicios de salud y educación
- Gestión de tareas y recordatorios

Contexto disponible:
{context}

Responde de manera útil, concisa y profesional en español."""

# ==================== FUNCIONES AUXILIARES ====================
def detect_country(text):
    """Detecta país en el texto"""
    text_lower = text.lower()
    country_keywords = {
        "argentina": ["argentina", "buenos aires"],
        "peru": ["peru", "perú", "lima"],
        "chile": ["chile", "santiago"],
        "mexico": ["mexico", "méxico", "cdmx"],
        "austria": ["austria", "viena"],
        "bulgaria": ["bulgaria", "sofia"],
        "croacia": ["croacia", "zagreb"],
        "bielorrusia": ["bielorrusia", "belarus", "minsk"],
        "serbia": ["serbia", "belgrado"],
        "eslovenia": ["eslovenia", "liubliana"],
        "macedonia": ["macedonia", "skopje"]
    }
    
    for country, keywords in country_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            return country
    return None

def detect_operator(text):
    """Detecta operadora"""
    text_lower = text.lower()
    if "claro" in text_lower:
        return "claro"
    elif "telcel" in text_lower:
        return "telcel"
    elif "a1" in text_lower:
        return "a1"
    return None

def detect_topic(text):
    """Detecta tema"""
    text_lower = text.lower()
    if any(word in text_lower for word in ["salud", "medico", "hospital", "doctor"]):
        return "health"
    elif any(word in text_lower for word in ["educacion", "curso", "aprender", "estudiar"]):
        return "education"
    return None

def get_context_for_query(prompt):
    """Determina qué contexto usar basado en la consulta"""
    country = detect_country(prompt)
    operator = detect_operator(prompt)
    topic = detect_topic(prompt)
    
    # Salud o Educación
    if topic == "health":
        return "Información sobre servicios de salud, telemedicina y cuidados médicos."
    elif topic == "education":
        return "Información sobre plataformas educativas, cursos y programas de aprendizaje."
    
    # Telecomunicaciones
    if operator == "telcel" or country == "mexico":
        return "Información sobre Telcel México: planes, servicios y promociones."
    elif operator == "claro":
        if country == "argentina":
            return "Información sobre Claro Argentina: planes móviles, internet y servicios."
        elif country == "peru":
            return "Información sobre Claro Perú: planes y servicios disponibles."
        elif country == "chile":
            return "Información sobre Claro Chile: ofertas y servicios."
        else:
            return "Información general sobre Claro en Latinoamérica."
    elif operator == "a1":
        return "Información sobre A1 Group en Europa Central y del Este."
    
    # Por defecto
    return "Información general sobre telecomunicaciones, salud y educación."

def call_groq_api_directly(messages):
    """Llamada directa a la API de Groq como fallback"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

# ==================== FUNCIONES PARA SERVIR ARCHIVOS ESTÁTICOS ====================
def get_frontend_path():
    """Obtener la ruta absoluta al frontend"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, '../frontend')

# ==================== ENDPOINTS ====================
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy", 
        "service": "Telecom Copilot API",
        "ai_ready": client is not None or GROQ_API_KEY is not None
    })

@app.route('/chat', methods=['POST'])
def chat():
    """Endpoint principal de chat"""
    try:
        if not client and not GROQ_API_KEY:
            return jsonify({
                "success": False,
                "error": "Servicio de IA no disponible"
            }), 503
        
        data = request.get_json()
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({
                "success": False,
                "error": "Mensaje vacío"
            }), 400
        
        # Obtener contexto
        context = get_context_for_query(user_message)
        
        # Preparar mensajes para Groq
        formatted_prompt = SYSTEM_PROMPT.format(context=context)
        
        messages = [
            {"role": "system", "content": formatted_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # Llamar a Groq - con fallback para diferentes versiones
        if client and client != "api_fallback":
            # Usar cliente Groq normal
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            response = completion.choices[0].message.content
        else:
            # Usar API directa como fallback
            result = call_groq_api_directly(messages)
            response = result["choices"][0]["message"]["content"]
        
        return jsonify({
            "success": True,
            "response": response
        })
        
    except Exception as e:
        logger.error(f"Error en /chat: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ==================== SERVIR FRONTEND - VERSIÓN MEJORADA ====================
@app.route('/')
def serve_frontend():
    """Servir el frontend HTML"""
    try:
        frontend_path = get_frontend_path()
        return send_from_directory(frontend_path, 'index.html')
    except Exception as e:
        logger.error(f"Error sirviendo index.html: {str(e)}")
        return f"""
        <html>
            <body>
                <h1>Telecom Copilot</h1>
                <p>Error cargando la interfaz: {str(e)}</p>
                <p>El backend está funcionando. Prueba <a href="/health">/health</a></p>
            </body>
        </html>
        """, 500

@app.route('/<path:path>')
def serve_static(path):
    """Servir archivos estáticos"""
    try:
        frontend_path = get_frontend_path()
        
        # Determinar content-type basado en extensión
        content_type = 'text/plain'
        if path.endswith('.css'):
            content_type = 'text/css'
        elif path.endswith('.js'):
            content_type = 'application/javascript'
        elif path.endswith('.png'):
            content_type = 'image/png'
        elif path.endswith('.jpg') or path.endswith('.jpeg'):
            content_type = 'image/jpeg'
        elif path.endswith('.ico'):
            content_type = 'image/x-icon'
        
        response = send_from_directory(frontend_path, path)
        response.headers['Content-Type'] = content_type
        return response
            
    except Exception as e:
        logger.error(f"Error sirviendo archivo estático {path}: {str(e)}")
        return f"Archivo no encontrado: {path}", 404

# ==================== ENDPOINT DE DIAGNÓSTICO ====================
@app.route('/debug')
def debug_info():
    """Endpoint de diagnóstico"""
    frontend_path = get_frontend_path()
    
    info = {
        "frontend_path": frontend_path,
        "frontend_exists": os.path.exists(frontend_path),
        "index_html_exists": os.path.exists(os.path.join(frontend_path, 'index.html')),
        "files_in_frontend": os.listdir(frontend_path) if os.path.exists(frontend_path) else []
    }
    
    return jsonify(info)

# ==================== CONFIGURACIÓN CORS PARA MÓVILES ====================
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# ==================== EJECUCIÓN ====================
if __name__ == '__main__':
    logger.info(f"🚀 Iniciando servidor Flask en http://localhost:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)

