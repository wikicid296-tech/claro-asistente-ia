from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
import os
from dotenv import load_dotenv
import logging

# ==================== CONFIGURACIÓN ====================
load_dotenv()

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PORT = int(os.getenv("PORT", 5000))

# Inicializar cliente Groq
try:
    client = Groq(api_key=GROQ_API_KEY)
    logger.info("✅ Cliente Groq inicializado correctamente")
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

# ==================== ENDPOINTS ====================
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy", 
        "service": "Telecom Copilot API",
        "ai_ready": client is not None
    })

@app.route('/chat', methods=['POST'])
def chat():
    """Endpoint principal de chat"""
    try:
        if not client:
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
        
        # Llamar a Groq
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        
        response = completion.choices[0].message.content
        
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

# ==================== SERVIR FRONTEND ====================
@app.route('/')
def serve_frontend():
    """Servir el frontend HTML"""
    try:
        with open('../frontend/index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error cargando frontend: {str(e)}", 500

@app.route('/<path:path>')
def serve_static(path):
    """Servir archivos estáticos"""
    try:
        # Intentar servir desde frontend/styles/
        if path.startswith('styles/'):
            with open(f'../frontend/{path}', 'r', encoding='utf-8') as f:
                return f.read(), 200, {'Content-Type': 'text/css'}
        
        # Intentar servir desde frontend/js/
        elif path.startswith('js/'):
            with open(f'../frontend/{path}', 'r', encoding='utf-8') as f:
                return f.read(), 200, {'Content-Type': 'application/javascript'}
        
        # Por defecto, intentar servir el archivo
        with open(f'../frontend/{path}', 'r', encoding='utf-8') as f:
            return f.read()
            
    except Exception as e:
        return f"Archivo no encontrado: {path}", 404

# ==================== EJECUCIÓN ====================
if __name__ == '__main__':
    logger.info(f"🚀 Iniciando servidor Flask en http://localhost:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=True)