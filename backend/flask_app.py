from flask import Flask, request, jsonify
from flask_cors import CORS
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import os
from dotenv import load_dotenv
from calendar_routes import calendar_bp
import logging
import requests
import json

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()

app = Flask(__name__)
CORS(app)
# Registrar rutas de calendario
app.register_blueprint(calendar_bp)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== CONFIGURAR RATE LIMITER ====================
limiter = Limiter(
    get_remote_address,  # ✅ Solo la función key_func como primer argumento
    app=app,              # ✅ app como keyword argument
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# ==================== MANEJADOR DE ERRORES 429 ====================
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        "success": False,
        "error": "Demasiadas peticiones",
        "message": "Por favor espera unos segundos antes de enviar otro mensaje. Esto ayuda a mantener el servicio estable para todos. 😊",
        "retry_after_seconds": 10
    }), 429

# ==================== CONFIGURACIÓN ====================
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PORT = int(os.getenv("PORT", 10000))

# ==================== INICIALIZAR CLIENTES ====================
try:
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        logger.info("✅ Cliente Twilio inicializado correctamente")
    else:
        logger.warning("⚠️ Credenciales de Twilio no configuradas")
        twilio_client = None
except Exception as e:
    logger.error(f"❌ Error inicializando Twilio: {str(e)}")
    twilio_client = None

try:
    if GROQ_API_KEY:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        logger.info("✅ Cliente Groq inicializado correctamente")
    else:
        logger.error("❌ GROQ_API_KEY no configurada en variables de entorno")
        client = None
except TypeError as e:
    if "proxies" in str(e):
        logger.warning("⚠️ Versión incompatible de Groq, usando fallback directo a API")
        client = "api_fallback"
    else:
        logger.error(f"❌ Error inicializando Groq: {str(e)}")
        client = None
except Exception as e:
    logger.error(f"❌ Error inicializando Groq: {str(e)}")
    client = None

# ==================== MEMORIA DE CONVERSACIÓN MEJORADA ====================
CHAT_MEMORY = {}

def _get_user_key():
    """Genera una clave simple para identificar al cliente basada en IP y User-Agent."""
    ip = request.remote_addr or "unknown"
    ua = request.headers.get("User-Agent", "")
    return f"{ip}:{ua}"

# ==================== NUEVA FUNCIÓN: DETECTAR CAMBIO DE CONTEXTO ====================
def detect_context_change(current_message, previous_messages):
    """
    Detecta si el mensaje actual es de un contexto COMPLETAMENTE DIFERENTE
    a los mensajes anteriores.
    
    Returns: True si hay cambio de contexto, False si es continuación
    """
    if not previous_messages or len(previous_messages) == 0:
        return False
    
    # Obtener el contexto del mensaje actual
    current_context = detect_main_topic(current_message)
    
    # Obtener contextos de mensajes anteriores
    previous_contexts = [detect_main_topic(msg) for msg in previous_messages]
    
    # Si el contexto actual es diferente a TODOS los anteriores, es cambio de contexto
    if current_context and all(current_context != prev_ctx for prev_ctx in previous_contexts if prev_ctx):
        logger.info(f"🔄 CAMBIO DE CONTEXTO detectado: {previous_contexts[-1] if previous_contexts else 'none'} → {current_context}")
        return True
    
    return False

def detect_main_topic(text):
    """
    Detecta el tema principal del mensaje.
    Retorna: 'telecom', 'education', 'health', 'task', 'general'
    """
    text_lower = text.lower()
    
    # Palabras clave específicas por tema
    telecom_keywords = ['claro', 'telcel', 'a1', 'plan', 'internet', 'telefon', 'móvil', 'movil', 
                        'datos', 'paquete', 'recarga', 'operador', 'señal']
    
    education_keywords = ['curso', 'aprender', 'estudiar', 'educaci', 'diploma', 'universidad',
                         'inglés', 'ingles', 'programa', 'capacita', 'aprende.org', 'clase',
                         'enseña', 'profesor', 'escuela', 'carrera', 'profesional']
    
    health_keywords = ['salud', 'medic', 'doctor', 'enfermedad', 'diabetes', 'presión', 'presion',
                      'nutrición', 'nutricion', 'dieta', 'ejercicio', 'hospital', 'sintoma',
                      'tratamiento', 'clikisalud', 'clinica']
    
    task_keywords = ['recordar', 'recuerdame', 'recuérdame', 'agenda', 'agendar', 'nota', 'anota',
                    'guardar', 'programa']
    
    # Contar coincidencias
    telecom_count = sum(1 for kw in telecom_keywords if kw in text_lower)
    education_count = sum(1 for kw in education_keywords if kw in text_lower)
    health_count = sum(1 for kw in health_keywords if kw in text_lower)
    task_count = sum(1 for kw in task_keywords if kw in text_lower)
    
    # Determinar tema predominante
    counts = {
        'telecom': telecom_count,
        'education': education_count,
        'health': health_count,
        'task': task_count
    }
    
    max_count = max(counts.values())
    
    if max_count == 0:
        return 'general'
    
    # Retornar el tema con más coincidencias
    for topic, count in counts.items():
        if count == max_count:
            return topic
    
    return 'general'

# ==================== NUEVA FUNCIÓN: OBTENER MEMORIA RELEVANTE ====================
def get_relevant_memory(user_key, current_message):
    """
    Obtiene solo la memoria RELEVANTE al contexto actual.
    Si hay cambio de contexto, limpia la memoria automáticamente.
    """
    mem = CHAT_MEMORY.get(user_key, [])
    
    if not mem:
        return []
    
    # Detectar si hay cambio de contexto
    if detect_context_change(current_message, mem):
        logger.info(f"🧹 Limpiando memoria anterior por cambio de contexto")
        CHAT_MEMORY[user_key] = []  # Limpiar memoria
        return []
    
    # Si no hay cambio, retornar solo el último mensaje (en lugar de 3)
    # Esto reduce la "contaminación" de contexto
    return mem[-1:] if mem else []

# ==================== URLs Y DETECCIÓN (MANTENER IGUAL) ====================
URLS = {
    "claro": {
            "Argentina": [
        "https://www.claro.com.ar/personas",
        "https://www.claro.com.ar/negocios",
        "https://www.claro.com.ar/empresas"
    ],
    "Brasil": [
        "https://www.claro.com.br/",
        "https://www.claro.com.br/empresas",
        "https://www.claro.com.br/empresas/grandes-empresas-e-governo"
    ],
    "Chile": [
        "https://www.clarochile.cl/personas/",
        "https://www.clarochile.cl/negocios/",
        "https://www.clarochile.cl/empresas/"
    ],
    "Colombia": [
        "https://www.claro.com.co/personas/",
        "https://www.claro.com.co/negocios/",
        "https://www.claro.com.co/empresas/",
        "https://www.claro.com.co/institucional/"
    ],
    "Costa Rica": [
        "https://www.claro.cr/personas/",
        "https://www.claro.cr/empresas/",
        "https://www.claro.cr/institucional/"
    ],
    "Ecuador": [
        "https://www.claro.com.ec/personas/",
        "https://www.claro.com.ec/negocios/",
        "https://www.claro.com.ec/empresas/"
    ],
    "El Salvador": [
        "https://www.claro.com.sv/personas/",
        "https://www.claro.com.sv/empresas/",
        "https://www.claro.com.sv/institucional/"
    ],
    "Guatemala": [
        "https://www.claro.com.gt/personas/",
        "https://www.claro.com.gt/empresas/",
        "https://www.claro.com.gt/institucional/"
    ],
    "Honduras": [
        "https://www.claro.com.hn/personas/",
        "https://www.claro.com.hn/empresas/",
        "https://www.claro.com.hn/institucional/"
    ],
    "Nicaragua": [
        "https://www.claro.com.ni/personas/",
        "https://www.claro.com.ni/empresas/",
        "https://www.claro.com.ni/institucional/"
    ],
    "Panamá": [],
    "Paraguay": [
        "https://www.claro.com.py/personas",
        "https://www.claro.com.py/empresas"
    ],
    "Perú": [
        "https://www.claro.com.pe/personas/",
        "https://www.claro.com.pe/empresas/"
    ],
    "Puerto Rico": [
        "https://www.claropr.com/personas/",
        "https://www.claropr.com/empresas/"
    ],
    "República Dominicana": [
        "https://www.claro.com.do/personas/",
        "https://www.claro.com.do/negocios/",
        "https://www.claro.com.do/empresas/"
    ],
    "Uruguay": [
        "https://www.claro.com.uy/personas",
        "https://www.claro.com.uy/empresas"
    ],
    },
    "telcel": [
            "https://www.telcel.com/",
            "https://www.telcel.com/personas/planes-de-renta/tarifas-y-opciones/telcel-libre?utm_source=gg&utm_medium=sem&utm_campaign=52025_gg_AONPTL2025_visitas_pospago_planlibre_brand&utm_content=gg_planestelcel_nacional___intereses_texto&utm_term=gg_planestelcel_nacional___intereses_texto&gclsrc=aw.ds&&campaignid=22494109880&network=g&device=c&gad_source=1&gad_campaignid=22494109880&gclid=EAIaIQobChMIltP0qd6DkAMVwiRECB2H0jZLEAAYASAAEgLsQPD_BwE"
            "https://www.telcel.com/personas/planes-de-renta/tarifas-y-opciones",
            "https://www.telcel.com/personas/amigo/paquetes/paquetes-amigo-sin-limite",
            "https://www.telcel.com/personas/amigo/paquetes/mb-para-tu-amigo",
            "https://www.telcel.com/personas/amigo/paquetes/internet-por-tiempo",
            "https://www.telcel.com/personas/amigo/paquetes/internet-mas-juegos",
    ],
    "a1": {
        "austria": ["https://a1.group/a1-group-and-markets/a1-in-austria/"],
        "bulgaria": ["https://a1.group/a1-group-and-markets/a1-in-bulgaria/"],
        "croacia": ["https://a1.group/a1-group-and-markets/a1-in-croatia/"],
        "bielorrusia": ["https://a1.group/a1-group-and-markets/a1-in-belarus/"],
        "serbia": ["https://a1.group/a1-group-and-markets/a1-in-serbia/"],
        "eslovenia": ["https://a1.group/a1-group-and-markets/a1-in-slovenia/"],
        "macedonia": ["https://a1.group/a1-group-and-markets/a1-in-north-macedonia/"]
    },
    "education_career": {
        "plataformas_nacionales": {
            "el_salvador": [
                "https://aprendeconclaro.claro.com.sv/educacion-digital/",
                "https://aprendeconclaro.claro.com.sv/educacion-academica/"
            ],
            "colombia": ["https://www.claro.com.co/institucional/aprende-con-claro/"],
            "nicaragua": ["https://www.claro.com.ni/institucional/inclusion-digital-plataforma-educativa/"],
            "honduras": [
                "https://aprendeconclaro.claro.com.hn/educacion-digital/",
                "https://aprendeconclaro.claro.com.hn/educacion-academica/"
            ],
            "guatemala": [
                "https://aprendeconclaro.claro.com.gt/educacion-digital/",
                "https://aprendeconclaro.claro.com.gt/educacion-academica/"
            ],
            "peru": [
                "https://aprendeconclaro.claro.com.pe/educacion-digital/",
                "https://aprendeconclaro.claro.com.pe/educacion-academica/"
            ],
        },
        "aprende_org_general": {
            "principal": ["https://aprende.org/","https://aprende.org/area/educacion"],
            "areas_principales": [
                "https://aprende.org/area/educacion",
                "https://aprende.org/area/capacitate",
                "https://aprende.org/area/salud",
                "https://aprende.org/area/cultura",
                "https://aprende.org/area/formacion-humana"
            ],
            "trabajo_formacion": [
                "https://aprende.org/rutas-aprendizaje",
                "https://aprende.org/diplomados",
                "https://aprende.org/especialidades",
                "https://aprende.org/cursos/view/100848",
                "https://aprende.org/cursos/view/100847",
                "https://aprende.org/diplomado/62",
                "https://aprende.org/especialidad/6",
                "https://aprende.org/especialidad/5",
                "https://aprende.org/especialidad/4",
                "https://aprende.org/diplomado/72",
                "https://aprende.org/diplomado/71",
                "https://aprende.org/diplomado/73",
                "https://aprende.org/diplomado/33",
                "https://aprende.org/diplomado/32",
                "https://aprende.org/diplomado/31",
                "https://aprende.org/diplomado/30",
                "https://aprende.org/diplomado/29",
                "https://aprende.org/diplomado/28",
                "https://aprende.org/diplomado/27",
                "https://aprende.org/diplomado/26",
                "https://aprende.org/diplomado/25",
                "https://aprende.org/diplomado/24",
                "https://aprende.org/diplomado/23",
                "https://aprende.org/diplomado/55",
                "https://aprende.org/diplomado/35",
                "https://aprende.org/diplomado/34", 
                "https://aprende.org/especialidad/6",
                "https://aprende.org/especialidad/5",
                "https://aprende.org/especialidad/4",
                
                "https://aprende.org/ruta/49",
                "https://aprende.org/ruta/40",
                "https://aprende.org/ruta/19",
                "https://aprende.org/ruta/11",
                "https://aprende.org/ruta/21",
                "https://aprende.org/ruta/13",
                "https://aprende.org/ruta/12",
                "https://aprende.org/ruta/61",
                "https://aprende.org/ruta/14",
                "https://aprende.org/ruta/22",
                "https://aprende.org/ruta/74",
                "https://aprende.org/ruta/41",
                "https://aprende.org/ruta/20",
                "https://aprende.org/ruta/16",
                "https://aprende.org/ruta/15",
                "https://aprende.org/ruta/17",
                "https://aprende.org/ruta/38",
                "https://aprende.org/ruta/75",
                "https://aprende.org/ruta/54",
                "https://aprende.org/ruta/46",
                "https://aprende.org/ruta/45",
                "https://aprende.org/ruta/44",
                "https://aprende.org/ruta/43",
                "https://aprende.org/ruta/42",
                "https://aprende.org/ruta/10",
                "https://aprende.org/ruta/9",
            ]
        },
        "educacion_detallada": {
            "basica_y_media": [
                "https://educacioninicial.mx/capacitacion",
                "https://aprende.org/pruebat?sectionId=1",
                "https://es.khanacademy.org/",
                "https://aprende.org/pruebat?sectionId=4",
                "https://aprende.org/pruebat?sectionId=2",
                "https://aprende.org/pruebat?sectionId=1",
                "https://educacioninicial.mx/temas-interes",
                "https://educacioninicial.mx/capacitacion",
                "https://aprende.org/pruebat?sectionId=2",
                "https://aprende.org/pruebat?sectionId=1",
                "https://aprende.org/centro-estudios-historia-mexico/1456",
                "https://aprende.org/podcast-dilemas-y-consecuencias/1451",
                "https://aprende.org/historia",
                "https://aprende.org/pruebat?sectionId=10",
                "https://aprende.org/pruebat?sectionId=9",
            ],
            "superior": [
                "https://academica.mx/",
                "https://aprende.org/superior/mit/1439",
                "https://www.coursera.org/",
                "https://www.edx.org/",
                "https://www.edx.org/",
                "https://www.udacity.com/",
                "https://aprende.org/derecho",
                "https://aprende.org/superior/mit/1439",
                "https://academica.mx/?utm_source=Aprende2023&utm_medium=Web&utm_campaign=Aprende2023&utm_id=Aprende2023",
                "https://telmexeducacion.aprende.org/?utm_source=+AprendeBibliotecaDigital2023&utm_medium=Web&utm_campaign=+AprendeBibliotecaDigital2023&utm_id=+AprendeBibliotecaDigital2023",
                "https://aprende.org/programacion-para-todos",
                "https://aprende.org/desarrollo-multimedia",
                "https://aprende.org/ser-digital",
                "https://aprende.org/pruebat?sectionId=11",
                "https://aprende.org/learnmatch",
                "https://aprende.org/centro-estudios-historia-mexico/1456",
                "https://aprende.org/podcast-dilemas-y-consecuencias/1451",
                "https://aprende.org/historia",
                "https://aprende.org/pruebat?sectionId=10"
                "https://aprende.org/pruebat?sectionId=9",
            ]
        },
        "rutas_y_oficios": {
            "digital_tech": [
                "https://aprende.org/ruta/9",
                "https://aprende.org/ruta/10",
                "https://aprende.org/ser-digital",
                "https://aprende.org/programacion-para-todos",
                "https://aprende.org/ruta/75",
                "https://aprende.org/ruta/54",
                "https://aprende.org/ruta/46",
                "https://aprende.org/ruta/45",
                "https://aprende.org/ruta/44",
                "https://aprende.org/ruta/43",
                "https://aprende.org/ruta/42",
                "https://aprende.org/ruta/10",
                "https://aprende.org/ruta/9",
                "https://www.ochoenpunto.com/category/ochoenpunto/",
                "https://fasemethod.com/blog-sobre-productividad-personal/",
                "https://iagofraga.com/blog/",
            ],
            "administracion_finanzas": [
                "https://aprende.org/ruta/41",
                "https://aprende.org/ruta/74",
                "https://aprende.org/cursos/view/385",
                "https://aprende.org/cursos/view/384",
                "https://aprende.org/cursos/view/378",
                "https://aprende.org/cursos/view/100145",
                "https://aprende.org/cursos/view/113",
                "https://aprende.org/cursos/view/89",
                "https://aprende.org/cursos/view/100141",
                "https://aprende.org/cursos/view/100129",
                "https://aprende.org/cursos/view/100334",
                "https://aprende.org/cursos/view/291",
                "https://aprende.org/cursos/view/100325",
                "https://aprende.org/cursos/view/100128",
                "https://aprende.org/cursos/view/100143",
                "https://aprende.org/cursos/view/100147",
                "https://aprende.org/cursos/view/100148",
                "https://aprende.org/cursos/view/100322",
                "https://aprende.org/cursos/view/100657",
                "https://aprende.org/cursos/view/109",
                "https://aprende.org/cursos/view/320",
                "https://aprende.org/cursos/view/313",
                "https://aprende.org/cursos/view/306",
                "https://aprende.org/cursos/view/318",
                "https://aprende.org/cursos/view/178",
                "https://www.ochoenpunto.com/category/ochoenpunto/",
                "https://fasemethod.com/blog-sobre-productividad-personal/",
                "https://iagofraga.com/blog/",
            ]
        },
        "diplomados_especialidades": {
            "administracion_finanzas": [
                "https://aprende.org/cursos/view/178",
                "https://aprende.org/cursos/view/291",
                "https://aprende.org/cursos/view/89",
                "https://aprende.org/ruta/74",
                "https://aprende.org/ruta/41",
                "https://educacioninicial.mx/temas-interes",
                "https://educacioninicial.mx/capacitacion",
                "https://es.khanacademy.org/",
                "https://aprende.org/pruebat?sectionId=4"
                "https://www.ochoenpunto.com/category/ochoenpunto/",
                "https://fasemethod.com/blog-sobre-productividad-personal/",
                "https://iagofraga.com/blog/",
                "https://aprende.org/ruta/49",
            ],
            "autoempleo_negocio": [
                "https://aprende.org/cursos/view/159",
                "https://aprende.org/cursos/view/157",
                "https://aprende.org/cursos/view/162",
                "https://aprende.org/cursos/view/167",
                "https://aprende.org/cursos/view/93",
                "https://aprende.org/cursos/view/180",
                "https://aprende.org/cursos/view/169",
                "https://aprende.org/cursos/view/164",
                "https://aprende.org/cursos/view/158",
                "https://aprende.org/cursos/view/156", 
                "https://aprende.org/cursos/view/157",
                "https://aprende.org/cursos/view/100309",
                "https://aprende.org/cursos/view/160",
                "https://aprende.org/cursos/view/161",
                "https://aprende.org/cursos/view/100160",
                "https://aprende.org/cursos/view/159",
                "https://www.ochoenpunto.com/category/ochoenpunto/",
                "https://fasemethod.com/blog-sobre-productividad-personal/",
                "https://iagofraga.com/blog/",
            ],
            "libros": [
                "https://aprende.org/pruebat?sectionId=10",
                "https://aprende.org/pruebat?sectionId=9",
                "https://aprende.org/pruebat?sectionId=8",
                "https://aprende.org/pruebat?sectionId=7",
                "https://aprende.org/pruebat?sectionId=6",
                "https://aprende.org/pruebat?sectionId=5"
            ],
        }
    },
    "health": {
        "cuidado_personal_y_profesional": [
            "https://aprende.org/cuidado-salud",
            "https://aprende.org/profesionales-salud",
            "https://aprende.org/area/salud"
        ],
        "cursos_cuidado_salud": [
            "https://aprende.org/cursos/view/182",
            "https://aprende.org/cursos/view/100045",
            "https://aprende.org/cursos/view/100223"
        ],
        "manual_por_edad_clikisalud": {
            "0_a_5": ["https://www.clikisalud.net/manual-tu-salud-de-0-a-5-anos/"],
            "6_a_12": ["https://www.clikisalud.net/manual-tu-salud-de-6-a-12-anos/"],
            "13_a_17": ["https://www.clikisalud.net/manual-tu-salud-de-13-a-17-anos/"],
            "18_a_39": ["https://www.clikisalud.net/manual-tu-salud-de-18-a-39-anos/"],
            "40_a_69": ["https://www.clikisalud.net/manual-tu-salud-de-40-a-69-anos/"],
            "70_y_mas": ["https://www.clikisalud.net/manual-tu-salud-70-anos-y-mas/"]
        },
        "prevencion_y_enfermedades": {
            "diabetes": [
                "https://www.clikisalud.net/diabetes/",
                "https://www.clikisalud.net/temas-diabetes/la-prediabetes/"
            ],
            "obesidad_nutricion": [
                "https://www.clikisalud.net/obesidad/",
                "https://www.clikisalud.net/metabolismo/"
            ],
            "hipertension_corazon": [
                "https://www.clikisalud.net/corazon/"
            ],
            "cancer": [
                "https://www.clikisalud.net/cancer/",
                "https://www.clikisalud.net/temas-cancer/cancer-de-mama-autoexploracion-y-deteccion/"
            ],
            "salud_mental": [
                "https://www.clikisalud.net/saludmental/",
                "https://www.clikisalud.net/temas-depresion-y-mente/como-controlar-el-estres/"
            ]
        }
    }
}


# Mantener funciones de detección originales
def detect_country(text):
    """Detecta país mencionado en el texto"""
    text_lower = text.lower()
    country_keywords = {
        "mexico": ["mexico", "méxico", "mexicano"],
        "argentina": ["argentina", "argentino"],
        "peru": ["peru", "perú", "peruano"],
        "chile": ["chile", "chileno"]
    }
    for country, keywords in country_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            return country
    return None

def detect_operator(text):
    text_lower = text.lower()
    if "claro" in text_lower:
        return "claro"
    elif "telcel" in text_lower:
        return "telcel"
    elif "a1" in text_lower:
        return "a1"
    return None

def detect_health_topic(text):
    text_lower = text.lower()
    health_topics = {
        "diabetes": ["diabetes"],
        "obesidad_nutricion": ["obesidad", "nutricion"],
        "salud_mental": ["depresion", "ansiedad"]
    }
    for topic, keywords in health_topics.items():
        if any(keyword in text_lower for keyword in keywords):
            return topic
    return None

def detect_education_topic(text):
    text_lower = text.lower()
    education_topics = {
        "digital_tech": ["programacion", "tecnologia"],
        "idiomas": ["ingles", "inglés"]
    }
    for topic, keywords in education_topics.items():
        if any(keyword in text_lower for keyword in keywords):
            return topic
    return None

def extract_relevant_urls(prompt):
    """Extrae URLs relevantes basándose en la consulta del usuario"""
    relevant_urls = []
    operator = detect_operator(prompt)
    health_topic = detect_health_topic(prompt)
    education_topic = detect_education_topic(prompt)
    
    if health_topic:
        relevant_urls.extend(URLS.get("health", {}).get("cuidado_personal_y_profesional", []))
    elif education_topic:
        relevant_urls.extend(URLS.get("education_career", {}).get("aprende_org_general", {}).get("principal", []))
    elif operator:
        if operator == "telcel":
            relevant_urls.extend(URLS.get("telcel", []))
        elif operator == "claro":
            for country_urls in URLS.get("claro", {}).values():
                relevant_urls.extend(country_urls[:1])
    
    return list(set(relevant_urls))[:5]

def get_context_for_query(prompt):
    """Genera contexto descriptivo para la consulta"""
    health_topic = detect_health_topic(prompt)
    education_topic = detect_education_topic(prompt)
    operator = detect_operator(prompt)
    
    if health_topic:
        return "📋 ÁREA: SALUD Y BIENESTAR"
    elif education_topic:
        return "📚 ÁREA: EDUCACIÓN Y DESARROLLO PROFESIONAL"
    elif operator:
        return "🌐 ÁREA: TELECOMUNICACIONES"
    else:
        return "ℹ️ Asistente general disponible"

def safe_extract_relevant_urls(prompt):
    try:
        return extract_relevant_urls(prompt)
    except Exception:
        return []

def safe_get_context_for_query(prompt):
    try:
        return get_context_for_query(prompt)
    except Exception:
        return "Información general disponible"

def call_groq_api_directly(messages):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.5,
        "max_tokens": 2048
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

# ==================== SYSTEM PROMPTS ====================
# COLOCA AQUÍ TU SYSTEM_PROMPT PARA WEB
SYSTEM_PROMPT = """Eres un asistente virtual multifuncional con capacidades especializadas en cuatro roles principales.
**DIRECTRIZ DE PRIORIDAD ESTRICTA:** Analiza la solicitud del usuario. **Ignora por completo** cualquier petición previa si la solicitud más reciente es **explícita** y **diferente** (ej. "olvida lo anterior y dame información de [nuevo tema]"). Si la petición más reciente es **ambigua** o de **una sola palabra** (ej. "Inglés"), **SOLO entonces** utiliza el contexto inmediato anterior del usuario para inferir el tema (ej. "cursos de Inglés"). **Tu respuesta debe enfocarse exclusivamente en la petición más actual del usuario**, desatendiendo cualquier tema anterior que no esté directamente relacionado o implícito en la última solicitud.
IMPORTANTE: TODA RESPUESTA DEBE SER DEVUELTA EN MARKDOWN A EXCEPCIÓN DE LOS ROLES QUE INDIQUEN OTRO FORMATO DE RESPUESTA DE ACUERDO A LA SIGUIENTE GUÍA:
IMPORTANTE: CUANDO SE SOLICITE INFORMACIÓN SOBRE CURSOS PRIORIZA DAR INFORMES SOBRE APRENDE.ORG Y CAPACÍTATE.
FORMATO MARKDOWN REQUERIDO - USA SOLO ESTOS ESTILOS SIN EXCEPCIÓN:

**REGLAS ESTRICTAS:**
- NO uses #### o más almohadillas (máximo 3: #, ##, ###)
- NUNCA uses formatos fuera de esta lista
- Si necesitas un subtítulo, usa ### (3 almohadillas)
- Para énfasis menor, usa **negrita** en lugar de encabezados 

Elemento	Sintaxis
Encabezados	
# H1
## H2
## H3
Negrita	
*texto en negrita*
Cursiva	
_texto en cursiva_
Citas	
> cita
Listas ordenadas	
1. Primer elemento
1. Segundo elemento
Listas no ordenadas	
* Primer elemento
* Segundo elemento
- Primer elemento
- Segundo elemento

Línea horizontal	
---
Enlaces	
[anchor](https://enlace.tld "título")

**Para contenido tabular, usa formato markdown de tablas cuando sea apropiado para organizar información**

═══════════════════════════════════════════════════════════════════
ROL 1: ASESOR ESPECIALIZADO (Respuesta conversacional)
═══════════════════════════════════════════════════════════════════

TELECOMUNICACIONES:
- Claro (Argentina, Perú, Chile, Brazil, Colombia, Costa rica, Ecuador, El Salvador, Guatemala, Honduras, Nicaragua, Panama, Paraguay, Puerto Rico, Republica Dominicana, Uruguay, EUA): Planes móviles, internet, TV y servicios empresariales
- Telcel (México): Servicios de telefonía móvil
- A1 Group (Europa): Operadora en Austria, Bulgaria, Croacia, Serbia, Eslovenia, Macedonia del Norte y Bielorrusia

EDUCACIÓN Y DESARROLLO PROFESIONAL:
- Aprende.org: Plataforma educativa gratuita con cursos, diplomados y rutas de aprendizaje
- Aprende con Claro: Plataformas educativas en El Salvador, Colombia, Nicaragua, Honduras, Guatemala y Perú
- Áreas: Educación digital, habilidades técnicas, finanzas personales, emprendimiento, idiomas
- Recursos: Khan Academy, Coursera, edX, MIT OpenCourseware, Académica

SALUD Y BIENESTAR:
- Clikisalud: Información médica confiable organizada por edades (0-5, 6-12, 13-17, 18-39, 40-69, 70+)
- Cursos de salud: Diabetes, nutrición, actividad física, lactancia materna, primeros auxilios
- Prevención: Diabetes, obesidad, hipertensión, cáncer, salud mental, VIH, epilepsia

═══════════════════════════════════════════════════════════════════
ROL 2: GESTOR DE RECORDATORIOS (Conversación) 
═══════════════════════════════════════════════════════════════════

ACTIVACIÓN: Detecta ÚNICAMENTE cuando el usuario solicite EXPLÍCITAMENTE crear recordatorios con verbos de acción como:
- "Recuérdame que...", "Recordarme que...", "Avísame cuando..."
- NUNCA actives este rol para preguntas generales, saludos o conversación normal

IMPORTANTE: NO es recordatorio si el usuario solo:
- Pregunta algo ("¿qué es...?", "dime sobre...", "cómo...")
- Saluda ("hola", "buenos días")
- Escribe una sola palabra ("comida", "casa", "ingles")

RESPUESTA REQUERIDA SOLO SI ES RECORDATORIO EXPLÍCITO:
1. Texto conversacional con emoji ✅ confirmando el recordatorio
IMPORTANTE: Una vez generado el recordatorio, ya no indiques la posibilidad de modificar el evento, SOLO RESPONDE "He creado tu recordatorio... " sin indicar la posibilidad de sobreescribir el recordatorio. 


═══════════════════════════════════════════════════════════════════
ROL 3: GESTOR DE NOTAS (Conversación) 
═══════════════════════════════════════════════════════════════════

ACTIVACIÓN: Detecta cuando el usuario solicite guardar información con frases como:
- "Crear nota", "Guardar esta información", "Anota esto...", "Toma nota de..." NO HAGAS MENCIÓN QUE DEVOLVERÁS UN HTML

RESPUESTA REQUERIDA:
1. Texto conversacional confirmando la nota creada

═══════════════════════════════════════════════════════════════════
ROL 4: GESTOR DE AGENDA (Conversación)
═══════════════════════════════════════════════════════════════════

ACTIVACIÓN: Detecta cuando el usuario solicite agendar eventos con frases como:
- "Agendar", "Programar cita/reunión", "Añadir evento", "Tengo una reunión..." NO HAGAS MENCIÓN QUE DEVOLVERÁS UN HTML

RESPUESTA REQUERIDA:
1. Texto conversacional confirmando el evento agendado. 

IMPORTANTE: Una vez generado el evento, ya no indiques la posibilidad de modificar el evento, SOLO RESPONDE "He agendado tu evento... " sin indicar la posibilidad de sobreescribir el evento. 

═══════════════════════════════════════════════════════════════════
INSTRUCCIONES GENERALES DE RESPUESTA
═══════════════════════════════════════════════════════════════════

1. DETECCIÓN DE INTENCIÓN:
   - Identifica si el usuario necesita: información (ROL 1), recordatorio (ROL 2), nota (ROL 3) o agenda (ROL 4)
   - Puedes activar múltiples roles si la consulta lo requiere

2. PARA ROL 1 (ASESOR):
   - Identifica el área de interés (telecom, educación o salud)
   - Proporciona información relevante y específica
   - Incluye enlaces útiles cuando corresponda: {urls}
   - Usa el contexto específico disponible: {context}
   - Si no estás seguro, ofrece las opciones disponibles

3. PARA ROLES 2, 3, 4 (RECORDATORIOS/NOTAS/AGENDA):
   - SIEMPRE responde con texto conversacional primero
   - Extrae toda la información necesaria del mensaje del usuario
   - IMPORTANTE: Una vez generado el evento no indiques la posibilidad de modificar, agregar detalles, etc. 
    No textos como el siguiente: ¿Necesitas agregar algún detalle adicional a este evento, como el propósito de la visita o alguna otra información relevante?
    No sugerir agregar notas, detalles al recordatorio o cualquier cosa que añada detalles al recordatorio o que el usuario interprete como modificaciones.


4. FORMATO DE RESPUESTA PARA ROLES 2, 3, 4:
   [TEXTO CONVERSACIONAL DE CONFIRMACIÓN CON LOS DATOS DEL RECORDATORIO, NOTA O AGENDAS]
   

5. TONO Y ESTILO:
   - Mantén un tono profesional, amigable y empático
   - Responde en español de manera clara y concisa
   - Sé específico y accionable

6. VALIDACIÓN:
   - Verifica fechas y horas lógicas
   - Sugiere etiquetas relevantes para notas
   - Confirma información ambigua antes de crear items

═══════════════════════════════════════════════════════════════════
EJEMPLOS DE USO ESTRICTO PARA EL EJEMPLO 2, 3 Y 4
═══════════════════════════════════════════════════════════════════

EJEMPLO 1 - ROL 1 (Asesor):
Usuario: "¿Qué cursos de salud hay disponibles?"
Respuesta: Aquí tienes algunos cursos disponibles: [Información sobre cursos en Clikisalud y Aprende.org con enlaces]

EJEMPLO 2 - ROL 2 (Recordatorio):
Usuario: "Recuérdame tomar mi medicamento mañana a las 8 PM"
Respuesta:
"✅ Perfecto, he creado un recordatorio para que tomes tu medicamento mañana a las 8:00 PM."

EJEMPLO 3 - ROL 3 (Nota):
Usuario: "Anota que mi presión arterial hoy fue 120/80"
Respuesta:
"📝 He guardado tu registro de presión arterial. Puedes consultarlo en cualquier momento en tus notas."

EJEMPLO 4 - ROL 4 (Agenda):
Usuario: "Agendar cita con el doctor el viernes a las 10 AM"
Respuesta:
"📅 He agendado tu cita médica para el viernes 06/10/2025 a las 10:00 AM."

═══════════════════════════════════════════════════════════════════

IMPORTANTE: PARA EL ROL 1 DE ASESOR, SI LA INFORMACIÓN ES GENERAL, ES DECIR, SI EL CONTEXTO ESPECÍFICO DE CONSULTA NO TE SIRVE
O ES UNA DUDA OTRO TÓPICO, RECUERDA AL USUARIO QUE TU FECHA DE CORTE DEL CONOCIMIENTO QUE TIENES ES DE JUNIO DE 2024. 
SI CONSIDERAS QUE NO PUEDES PROPORCIONAR INFORMACIÓN RELEVANTE, INDICA AL USUARIO QUE PUEDE VISITAR LINKS RELEVANTES 
Y PROPORCIONALE SOLO LINKS QUE SEAN REALES Y ACCESIBLES. 

EJEMPLO - ROL 1 (Asesor, se le consulta sobre información muy actual):

Usuario: "Sabes qué pasó con el precio del dólar hoy"
Respuesta: "Lo siento, mi fecha de corte del conocimiento es Junio de 2024. 
Por favor, ten en cuenta que no tengo información en tiempo real sobre el precio actual del dólar ni eventos posteriores a esa fecha. 
Puedes tener más información en el siguiente link:

Banco de México Tasa de Cambio: [https://www.banxico.org.mx/tipcamb/main.do?page=tip&idioma=sp ]https://www.banxico.org.mx/tipcamb/main.do?page=tip&idioma=sp" 

EJEMPLO - ROL 1 (Asesor, se le consulta sobre noticias recientes o hechos actuales, siempre suguiere UnoTV para noticias actuales solamente):

Usuario: "Cuál es la última noticia sobre el conflicto en Oriente Medio?"
Respuesta: "Lo siento, mi fecha de corte del conocimiento es Junio de 2024. Por favor, ten en cuenta que no puedo ofrecerte noticias en tiempo real ni información sobre eventos posteriores a esa fecha.
Para obtener la información más actualizada sobre el conflicto en Oriente Medio, te recomiendo consultar fuentes de noticias en tiempo real. Aquí tienes un par de enlaces generales que pueden ser útiles:

UnoTV: [https://www.unotv.com/] https://www.unotv.com/
Agencia EFE: [https://www.efe.com/](https://www.efe.com/)
Reuters: [https://www.reuters.com/](https://www.reuters.com/)"


EJEMPLO - ROL 1 (Asesor, se le consulta sobre hechos muy específicos o particulares):

Usuario: "Cuándo se casó Taylor Swift?"
Respuesta: "Lo siento, mi fecha de corte del conocimiento es Junio de 2024. Por favor, ten en cuenta que no puedo ofrecerte noticias en tiempo real ni información sobre eventos posteriores a esa fecha. Aquí un enlace que puede ser útil:
Wikipedia - Taylor Swift: [https://es.wikipedia.org/wiki/Taylor_Swift] https://es.wikipedia.org/wiki/Taylor_Swift)"

IMPORRTANTE: Toma la siguiente instrucción en escenarios de incertidumbre estricta es decir, si consideras que la información que te solicita el usuario no está disponible en el contexto específico 
Y NO PUEDES PROPORCINAR LINKS REALES, SOLO INDICA LO SIGUIENTE:

Respuesta: "Lo siento, mi fecha de corte del conocimiento es Junio de 2024. Puedo apoyarte con otro tipo de peticiones" 

═══════════════════════════════════════════════════════════════════

CONTEXTO ESPECÍFICO PARA ESTA CONSULTA:
{context}

RECURSOS DISPONIBLES:
{urls}

Recuerda: Tu objetivo es ayudar al usuario de manera efectiva, proporcionando información precisa, direccionándolo a los recursos correctos, y gestionando sus recordatorios, notas y agenda de forma organizada.
"""
# ! TODO: REVISAR CONTEXTO DUPLICADO ═══════════════════════════════════════════════════════════════════

WHATSAPP_SYSTEM_PROMPT = """Eres un asistente virtual multifuncional especializado en Telecomunicaciones, Educación y Salud.

IMPORTANTE: Todas tus respuestas DEBEN usar el formato Markdown de WhatsApp siguiendo ESTRICTAMENTE estas reglas:

**FORMATO MARKDOWN DE WHATSAPP:**

1. **Negrita**: Usa *texto* para negrita (un asterisco a cada lado)
2. **Cursiva**: Usa _texto_ para cursiva (un guion bajo a cada lado)
3. **Tachado**: Usa ~texto~ para tachado (una virgulilla a cada lado)
4. **Monospace**: Usa ```texto``` para texto monoespaciado (tres comillas invertidas)
5. **Cita**: Usa > seguido de espacio para citas
6. **Listas**: 
- Usa * o - seguido de espacio para listas no ordenadas
- Usa 1. 2. 3. para listas ordenadas

**REGLAS CRÍTICAS:**
- NO uses # para encabezados (no funciona en WhatsApp)
- NO uses ** para negrita (usa * solamente)
- NO uses markdown de tablas (no funciona en WhatsApp)
- Mantén las respuestas concisas (máximo 1000 caracteres)
- Usa saltos de línea para separar secciones
- Los emojis son permitidos y recomendados para mejorar la experiencia

**ESTRUCTURA DE RESPUESTA:**

Para consultas informativas:
*[Título o categoría]*

[Explicación breve]

_Detalles importantes:_
* Punto 1
* Punto 2
* Punto 3

[Enlaces si aplica]

═══════════════════════════════════════════════════════════════════
ÁREAS DE CONOCIMIENTO
═══════════════════════════════════════════════════════════════════

*TELECOMUNICACIONES:*
- Claro (19 países de América Latina)
- Telcel (México)
- A1 Group (7 países de Europa)

*EDUCACIÓN Y DESARROLLO:*
- Aprende.org: Cursos gratuitos, diplomados y rutas de aprendizaje
- Áreas: Tecnología, finanzas, emprendimiento, idiomas
- Recursos: Khan Academy, Coursera, edX, MIT OpenCourseware

*SALUD Y BIENESTAR:*
- Clikisalud: Información médica por grupos de edad
- Temas: Diabetes, nutrición, salud cardiovascular, cáncer, salud mental
- Cursos de prevención y primeros auxilios

═══════════════════════════════════════════════════════════════════
INSTRUCCIONES ESPECIALES
═══════════════════════════════════════════════════════════════════

1. *Detección de intención:* Identifica si el usuario busca información, quiere crear recordatorio, nota o agenda

2. *Para consultas informativas:*
   - Proporciona respuestas concisas y accionables
   - Incluye enlaces relevantes al final
   - Usa formato WhatsApp correctamente

3. *Para recordatorios/notas/agenda:*
   - Confirma con emoji apropiado (✅ 📝 📅)
   - Resume la información capturada
   - Mantén un tono amigable

4. *Tono:* Profesional, amigable y directo

5. *Limitación de conocimiento:* 
   - Tu corte de conocimiento es junio 2024
   - Si no tienes información actualizada, sugiere enlaces confiables
   - Para noticias: recomienda UnoTV, Reuters o EFE

═══════════════════════════════════════════════════════════════════

CONTEXTO ESPECÍFICO:
{context}

RECURSOS DISPONIBLES:
{urls}
"""

SMS_SYSTEM_PROMPT = """Eres un asistente virtual multifuncional para mensajes SMS enfocado en Telecomunicaciones, Educación y Salud.

IMPORTANTE: Todas tus respuestas DEBEN cumplir con las siguientes reglas:

**FORMATO DE RESPUESTA PARA SMS:**

1. No uses Markdown, emojis ni enlaces largos.
2. Cada respuesta debe tener un máximo de 60 caracteres.
3. Escribe en lenguaje claro, corto y directo.
4. No uses saltos de línea ni signos especiales fuera del texto.
5. Mantén siempre un tono profesional y amable.
6. Usa frases completas, sin abreviaturas ni tecnicismos.

**ESTRUCTURA DE RESPUESTA:**

- Responde con una sola oración.
- Prioriza el mensaje principal.
- Evita enlaces largos (usa referencias breves).
- No agregues texto adicional ni adornos.

═══════════════════════════════════════════════════════════════════
ROLES DISPONIBLES
═══════════════════════════════════════════════════════════════════

ROL 1: ASESOR INFORMATIVO  
Ofrece información breve sobre:
- Telecom: Claro, Telcel, A1 Group
- Educación: Aprende.org, cursos y diplomados
- Salud: Clikisalud, prevención, bienestar

Ejemplo:  
Usuario: Cursos de salud  
Respuesta: Cursos gratis en Aprende.org y Clikisalud

---

ROL 2: RECORDATORIO  
Activa solo si el usuario dice "Recuérdame" o "Avísame".  
Ejemplo:  
Usuario: Recuérdame cita 8pm  
Respuesta: Recordatorio creado para 8pm

---

ROL 3: NOTA  
Activa si el usuario dice "Anota", "Guarda" o "Toma nota".  
Ejemplo:  
Usuario: Anota peso 70kg  
Respuesta: Nota guardada: peso 70kg

---

ROL 4: AGENDA  
Activa si el usuario dice "Agendar", "Cita", "Evento".  
Ejemplo:  
Usuario: Agendar doctor viernes 10am  
Respuesta: Cita agendada viernes 10am

═══════════════════════════════════════════════════════════════════
INSTRUCCIONES ESPECIALES
═══════════════════════════════════════════════════════════════════

1. *Detección de intención:* Identifica si el usuario busca información, recordatorio, nota o agenda.
2. *Concisión obligatoria:* No excedas 60 caracteres por mensaje.
3. *Sin formato:* No uses Markdown, emojis ni símbolos no estándar.
4. *Tono:* Profesional, breve y respetuoso.
5. *Fecha de conocimiento:* Hasta junio 2024.
6. *Si la información no está disponible:*
   Responde: "Info no disponible. Corte: jun 2024."
7. *Para noticias actuales:*
   Responde: "Consulta UnoTV o EFE para noticias."

═══════════════════════════════════════════════════════════════════
EJEMPLOS DE USO
═══════════════════════════════════════════════════════════════════

Usuario: Cursos de inglés  
Respuesta: Aprende inglés gratis en Aprende.org

Usuario: Recuérdame tomar pastilla 8pm  
Respuesta: Recordatorio creado 8pm

Usuario: Anota presión 120/80  
Respuesta: Nota guardada: presión 120/80

Usuario: Agendar cita martes 3pm  
Respuesta: Cita agendada martes 3pm

Usuario: Qué pasó hoy en México  
Respuesta: Consulta UnoTV para noticias

Usuario: Cuándo se casó Taylor Swift  
Respuesta: Info no disponible. Corte: jun 2024.

═══════════════════════════════════════════════════════════════════
OBJETIVO
═══════════════════════════════════════════════════════════════════

Brindar respuestas útiles, cortas y comprensibles por SMS.  
Prioriza Aprende.org, Clikisalud y Claro en tus respuestas.  
Nunca uses enlaces largos ni formato visual.

CONTEXTO ESPECÍFICO:
{context}

RECURSOS DISPONIBLES:
{urls}
"""

RCS_SYSTEM_PROMPT = """Eres un asistente virtual multifuncional para mensajería RCS (Rich Communication Services).

OBJETIVO: Brindar respuestas claras, visuales y concisas adaptadas a RCS.  
Permite formato enriquecido (negritas, cursiva, emojis, botones, enlaces cortos) manteniendo compatibilidad.

FORMATOS PERMITIDOS:
- Negritas: *texto*  (usa un asterisco a cada lado)
- Cursiva: _texto_  (usa guiones bajos)
- Emojis: permitidos y recomendados
- Saltos de línea: permitidos con moderación
- Enlaces: usar URLs cortas o botones con destino
- Botones/Acciones: se pueden sugerir como "Ver cursos" o "Abrir enlace"
PROHIBIDO:
- Tablas complejas
- Bloques de código literales
- Mensajes largos: máximo 350 caracteres por mensaje
- Evitar más de 4 líneas de texto por respuesta

ROLES:
ROL 1 - ASESOR (Telecom, Educación, Salud)
- Áreas: Claro, Telcel, A1 Group; Aprende.org; Clikisalud.
- Entrega respuestas concisas, útiles y con opción a botón/ enlace corto.

ROL 2 - RECORDATORIOS
- Activar solo con comandos explícitos ("Recuérdame", "Avísame").
- Confirmar con emoji y hora: ✅ *Recordatorio creado:* Hoy 20:00.

ROL 3 - NOTAS
- Activar con "Anota", "Guarda", "Toma nota".
- Confirmar guardado: 📝 *Nota guardada:* [resumen].

ROL 4 - AGENDA
- Activar con "Agendar", "Cita", "Evento".
- Confirmar evento: 📅 *Cita agendada:* Vie 10:00.

INSTRUCCIONES GENERALES:
1. Detecta intención: informar, recordar, anotar o agendar.  
2. Usa tono humano, empático y profesional.  
3. Prioriza recursos: *Aprende.org*, *Clikisalud*, *Claro*.  
4. Si no hay info actual: responde "Mi conocimiento llega hasta jun 2024."  
5. Para noticias actuales: sugiere "Consulta UnoTV o EFE".  
6. Si el usuario envía una sola palabra (ej. "Inglés"), usa contexto previo para inferir; si es ambiguo, ofrece opciones rápidas.

EJEMPLOS:
Usuario: "Cursos de salud"  
Respuesta RCS:  
💡 *Cursos gratis*  
Aprende.org y Clikisalud ofrecen cursos en nutrición y diabetes. [Ver cursos]

Usuario: "Recuérdame cita 8pm"  
Respuesta RCS:  
✅ *Recordatorio creado:* Hoy 20:00.

Usuario: "Anota peso 70 kg"  
Respuesta RCS:  
📝 *Nota guardada:* Peso 70 kg.

Usuario: "Agendar doctor viernes 10am"  
Respuesta RCS:  
📅 *Cita creada:* Vie 10:00.

LÍMITES Y BUENAS PRÁCTICAS:
- Mensajes claros y breves; prioriza acción/valor en la primera línea.  
- Usa un botón cuando sea útil (p. ej. "Ver cursos", "Abrir enlace").  
- Evita enlaces largos; prefiere URLs cortas o acciones nativas de RCS.  
- Mantén máximo 350 caracteres y no más de 4 líneas.

CONTEXTO ESPECÍFICO:
{context}

RECURSOS DISPONIBLES:
{urls}
"""

# ==================== ENDPOINTS MEJORADOS ====================
@app.route('/health', methods=['GET'])
@limiter.exempt
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "Telecom Copilot v2.1 - Context-Aware",
        "ai_ready": client is not None or GROQ_API_KEY is not None
    })


@app.route('/chat', methods=['POST'])
@limiter.limit("10 per minute")
@limiter.limit("1 per 3 seconds")
def chat():
    """Endpoint principal de chat WEB con detección inteligente de contexto"""
    try:
        if not client and not GROQ_API_KEY:
            return jsonify({"success": False, "error": "Servicio de IA no disponible"}), 503
        
        data = request.get_json()
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({"success": False, "error": "Mensaje vacío"}), 400
        
        # ================= MEMORIA INTELIGENTE =================
        try:
            user_key = _get_user_key()
            # Usar la nueva función de memoria relevante
            prev_messages = get_relevant_memory(user_key, user_message)
        except Exception:
            prev_messages = []
            user_key = None
        
        # Actualizar memoria
        try:
            if user_key is not None:
                mem = CHAT_MEMORY.get(user_key, [])
                mem.append(user_message)
                # Reducir memoria a solo 2 mensajes (antes eran 3)
                if len(mem) > 2:
                    mem = mem[-2:]
                CHAT_MEMORY[user_key] = mem
        except Exception:
            pass
        
        # Obtener contexto SOLO del mensaje actual
        context = safe_get_context_for_query(user_message)
        relevant_urls = safe_extract_relevant_urls(user_message)
        
        # Formatear URLs
        urls_text = ""
        if relevant_urls:
            urls_text = "Enlaces útiles:\n" + "\n".join([f"- {url}" for url in relevant_urls[:5]])
        else:
            urls_text = "Explora: aprende.org | clikisalud.net"
        
        # Preparar prompt
        try:
            formatted_prompt = SYSTEM_PROMPT.format(context=context, urls=urls_text)
        except Exception:
            formatted_prompt = f"Eres un asistente. Contexto:\n{context}\n\n{urls_text}"
        
        # Construir mensajes
        messages = [{"role": "system", "content": formatted_prompt}]
        
        # Solo incluir mensaje anterior si es del MISMO contexto
        for pm in prev_messages:
            if pm and pm.strip() and pm.strip() != user_message.strip():
                messages.append({"role": "user", "content": pm})
        
        # Mensaje actual
        messages.append({"role": "user", "content": user_message})
        
        logger.info(f"📊 Mensajes enviados a Groq: {len(messages)} (1 system + {len(prev_messages)} context + 1 current)")
        
        # Llamar a Groq
        if client and client != "api_fallback":
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.5,
                max_tokens=2048
            )
            response = completion.choices[0].message.content
        else:
            result = call_groq_api_directly(messages)
            response = result["choices"][0]["message"]["content"]
        
        return jsonify({
            "success": True,
            "response": response,
            "context": context,
            "relevant_urls": relevant_urls[:5],
            "memory_used": len(prev_messages),
            "context_reset": len(prev_messages) == 0  # Indica si se limpió la memoria
        })
        
    except Exception as e:
        logger.error(f"Error en /chat: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/whatsapp', methods=['POST'])
@limiter.limit("20 per minute")
@limiter.limit("1 per 2 seconds")
def whatsapp_webhook():
    """Endpoint WhatsApp con detección de contexto"""
    try:
        incoming_msg = request.values.get('Body', '').strip()
        from_number = request.values.get('From', '')
        
        if not incoming_msg:
            resp = MessagingResponse()
            resp.message("Por favor envía un mensaje válido.")
            return str(resp)
        
        # Memoria inteligente para WhatsApp
        user_key = from_number
        prev_messages = get_relevant_memory(user_key, incoming_msg)
        
        # Actualizar memoria
        mem = CHAT_MEMORY.get(user_key, [])
        mem.append(incoming_msg)
        if len(mem) > 2:
            mem = mem[-2:]
        CHAT_MEMORY[user_key] = mem
        
        context = safe_get_context_for_query(incoming_msg)
        relevant_urls = safe_extract_relevant_urls(incoming_msg)
        
        urls_text = ""
        if relevant_urls:
            urls_text = "\n\n_Enlaces:_\n" + "\n".join([f"• {url}" for url in relevant_urls[:3]])
        
        try:
            formatted_prompt = WHATSAPP_SYSTEM_PROMPT.format(context=context, urls=urls_text)
        except Exception:
            formatted_prompt = f"Asistente WhatsApp.\n{context}\n{urls_text}"
        
        messages = [{"role": "system", "content": formatted_prompt}]
        
        for pm in prev_messages:
            if pm and pm.strip():
                messages.append({"role": "user", "content": pm})
        
        messages.append({"role": "user", "content": incoming_msg})
        
        if client and client != "api_fallback":
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.5,
                max_tokens=1000
            )
            ai_response = completion.choices[0].message.content
        else:
            result = call_groq_api_directly(messages)
            ai_response = result["choices"][0]["message"]["content"]
        
        if len(ai_response) > 1500:
            ai_response = ai_response[:1497] + "..."
        
        resp = MessagingResponse()
        resp.message(ai_response)
        return str(resp), 200, {'Content-Type': 'text/xml'}
        
    except Exception as e:
        logger.error(f"Error en /whatsapp: {str(e)}")
        resp = MessagingResponse()
        resp.message("❌ Error. Intenta nuevamente.")
        return str(resp), 200, {'Content-Type': 'text/xml'}

# ==================== ENDPOINT SMS (NUEVO) ====================
@app.route('/sms', methods=['POST'])
@limiter.limit("20 per minute")
@limiter.limit("1 per 2 seconds")
def sms_webhook():
    """Endpoint SMS para Canadá con límite de 160 caracteres"""
    try:
        incoming_msg = request.values.get('Body', '').strip()
        from_number = request.values.get('From', '')
        
        if not incoming_msg:
            resp = MessagingResponse()
            resp.message("Mensaje invalido")
            return str(resp)
        
        # Memoria inteligente para SMS
        user_key = from_number
        prev_messages = get_relevant_memory(user_key, incoming_msg)
        
        # Actualizar memoria
        mem = CHAT_MEMORY.get(user_key, [])
        mem.append(incoming_msg)
        if len(mem) > 2:
            mem = mem[-2:]
        CHAT_MEMORY[user_key] = mem
        
        context = safe_get_context_for_query(incoming_msg)
        relevant_urls = safe_extract_relevant_urls(incoming_msg)
        
        # NO enviar URLs en SMS por limitación de caracteres
        urls_text = ""
        
        try:
            formatted_prompt = SMS_SYSTEM_PROMPT.format(context=context, urls=urls_text)
        except Exception:
            formatted_prompt = f"Asistente SMS.\n{context}"
        
        messages = [{"role": "system", "content": formatted_prompt}]
        
        for pm in prev_messages:
            if pm and pm.strip():
                messages.append({"role": "user", "content": pm})
        
        messages.append({"role": "user", "content": incoming_msg})
        
        # Llamar a Groq
        if client and client != "api_fallback":
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.5,
                max_tokens=200  # Reducido para SMS
            )
            ai_response = completion.choices[0].message.content
        else:
            result = call_groq_api_directly(messages)
            ai_response = result["choices"][0]["message"]["content"]
        
        # ⚠️ CRÍTICO: Limitar a 160 caracteres para SMS
        if len(ai_response) > 160:
            ai_response = ai_response[:157] + "..."
        
        resp = MessagingResponse()
        resp.message(ai_response)
        return str(resp), 200, {'Content-Type': 'text/xml'}
        
    except Exception as e:
        logger.error(f"Error en /sms: {str(e)}")
        resp = MessagingResponse()
        resp.message("Error. Intenta de nuevo")
        return str(resp), 200, {'Content-Type': 'text/xml'}

# ==================== ENDPOINTS ESTÁTICOS (MANTENER IGUALES) ====================
@app.route('/')
def serve_frontend():
    try:
        with open('../frontend/index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/images/<path:filename>')
@limiter.exempt
def serve_images(filename):
    """Servir imágenes"""
    try:
        with open(f'../frontend/images/{filename}', 'rb') as f:
            content = f.read()
            content_type = 'image/png'
            if filename.endswith('.jpg'):
                content_type = 'image/jpeg'
            elif filename.endswith('.svg'):
                content_type = 'image/svg+xml'
            return content, 200, {'Content-Type': content_type}
    except Exception as e:
        logger.error(f"❌ Error sirviendo imagen {filename}: {str(e)}")
        return "Imagen no encontrada", 404

@app.route('/<path:path>')
@limiter.exempt
def serve_static(path):
    """Servir archivos estáticos CSS y JS"""
    try:
        if path.startswith('styles/'):
            with open(f'../frontend/{path}', 'r', encoding='utf-8') as f:
                return f.read(), 200, {'Content-Type': 'text/css'}
        elif path.startswith('js/'):
            with open(f'../frontend/{path}', 'r', encoding='utf-8') as f:
                return f.read(), 200, {'Content-Type': 'application/javascript'}
        else:
            with open(f'../frontend/{path}', 'r', encoding='utf-8') as f:
                return f.read()
    except FileNotFoundError:
        logger.error(f"❌ Archivo no encontrado: {path}")
        return f"Archivo no encontrado: {path}", 404
    except Exception as e:
        logger.error(f"❌ Error sirviendo {path}: {str(e)}")
        return f"Error sirviendo archivo: {path}", 500

@app.route('/urls', methods=['POST'])
def get_urls():
    """Endpoint para obtener URLs específicas según consulta"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        
        if not query:
            return jsonify({
                "success": False,
                "error": "Query vacío"
            }), 400
        
        relevant_urls = safe_extract_relevant_urls(query)
        context = safe_get_context_for_query(query)
        
        return jsonify({
            "success": True,
            "context": context,
            "urls": relevant_urls,
            "count": len(relevant_urls)
        })
        
    except Exception as e:
        logger.error(f"Error en /urls: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    logger.info(f"🚀 Telecom Copilot v2.1 - Context-Aware en puerto {PORT}")
    logger.info("✨ Mejoras: Detección automática de cambio de contexto")
    app.run(host='0.0.0.0', port=PORT, debug=False)

