from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import logging
import requests
import json

load_dotenv()

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PORT = int(os.getenv("PORT", 10000))

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
    "telcel": ["https://www.telcel.com/",
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
            "principal": ["https://aprende.org/"],
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
                "https://aprende.org/especialidades"
            ]
        },
        "educacion_detallada": {
            "basica_y_media": [
                "https://educacioninicial.mx/capacitacion",
                "https://aprende.org/pruebat?sectionId=1",
                "https://es.khanacademy.org/"
            ],
            "superior": [
                "https://academica.mx/",
                "https://aprende.org/superior/mit/1439",
                "https://www.coursera.org/",
                "https://www.edx.org/"
            ]
        },
        "rutas_y_oficios": {
            "digital_tech": [
                "https://aprende.org/ruta/9",
                "https://aprende.org/ruta/10",
                "https://aprende.org/ser-digital",
                "https://aprende.org/programacion-para-todos"
            ],
            "administracion_finanzas": [
                "https://aprende.org/ruta/41",
                "https://aprende.org/ruta/74"
            ]
        },
        "diplomados_especialidades": {
            "administracion_finanzas": [
                "https://aprende.org/cursos/view/178",
                "https://aprende.org/cursos/view/291",
                "https://aprende.org/cursos/view/89"
            ],
            "autoempleo_negocio": [
                "https://aprende.org/cursos/view/159",
                "https://aprende.org/cursos/view/157"
            ]
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

# ==================== SYSTEM PROMPT MEJORADO ====================
SYSTEM_PROMPT = """Eres un asistente virtual multifuncional con capacidades especializadas en cuatro roles principales.

IMPORTANTE: TODA RESPUESTA DEBE SER DEVUELTA EN MARKDOWN A EXCEPCIÓN DE LOS ROLES QUE INDIQUEN OTRO FORMATO DE RESPUESTA DE ACUERDO A LA SIGUIENTE GUÍA:

FORMATO MARKDOWN REQUERIDO: 

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
 
+ Primer elemento
+ Segundo elemento
 
- Primer elemento
- Segundo elemento

Línea horizontal	
---
Enlaces	
[anchor](https://enlace.tld "título")

═══════════════════════════════════════════════════════════════════
ROL 1: ASESOR ESPECIALIZADO (Respuesta conversacional)
═══════════════════════════════════════════════════════════════════

TELECOMUNICACIONES:
- Claro (Argentina, Perú, Chile): Planes móviles, internet, TV y servicios empresariales
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

ACTIVACIÓN: Detecta cuando el usuario solicite crear recordatorios con frases como:
- "Crear recordatorio", "Recordarme que...", "No olvides avisarme..." NO HAGAS MENCIÓN QUE DEVOLVERÁS UN HTML

RESPUESTA REQUERIDA:
1. Texto conversacional confirmando el recordatorio

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
1. Texto conversacional confirmando el evento agendado

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
   - SIEMPRE incluye el HTML estructurado después entre los comentarios correspondientes
   - Extrae toda la información necesaria del mensaje del usuario

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
EJEMPLOS DE USO
═══════════════════════════════════════════════════════════════════

EJEMPLO 1 - ROL 1 (Asesor):
Usuario: "¿Qué cursos de salud hay disponibles?"
Respuesta: Aquí tienes algunos cursos disponibles: [Información sobre cursos en Clikisalud y Aprende.org con enlaces]

EJEMPLO 2 - ROL 2 (Recordatorio):
Usuario: "Recuérdame tomar mi medicamento mañana a las 8 PM"
Respuesta:
"✅ Perfecto, he creado un recordatorio para que tomes tu medicamento mañana a las 8:00 PM. Te avisaré con anticipación."

EJEMPLO 3 - ROL 3 (Nota):
Usuario: "Anota que mi presión arterial hoy fue 120/80"
Respuesta:
"📝 He guardado tu registro de presión arterial. Puedes consultarlo en cualquier momento en tus notas."

EJEMPLO 4 - ROL 4 (Agenda):
Usuario: "Agendar cita con el doctor el viernes a las 10 AM"
Respuesta:
"📅 He agendado tu cita médica para el viernes 06/10/2025 a las 10:00 AM. Te enviaré un recordatorio antes de la cita."

═══════════════════════════════════════════════════════════════════

CONTEXTO ESPECÍFICO PARA ESTA CONSULTA:
{context}

RECURSOS DISPONIBLES:
{urls}

Recuerda: Tu objetivo es ayudar al usuario de manera efectiva, proporcionando información precisa, direccionándolo a los recursos correctos, y gestionando sus recordatorios, notas y agenda de forma organizada.
"""

# ==================== FUNCIONES DE DETECCIÓN MEJORADAS ====================

def detect_country(text):
    """Detecta país mencionado en el texto"""
    text_lower = text.lower()
    country_keywords = {
        "argentina": ["argentina", "argentino", "buenos aires", "arg"],
        "peru": ["peru", "perú", "peruano", "lima"],
        "chile": ["chile", "chileno", "santiago"],
        "mexico": ["mexico", "méxico", "mexicano", "cdmx", "ciudad de mexico"],
        "el_salvador": ["el salvador", "salvador", "salvadoreño", "san salvador"],
        "colombia": ["colombia", "colombiano", "bogota", "bogotá"],
        "nicaragua": ["nicaragua", "nicaraguense", "managua"],
        "honduras": ["honduras", "hondureño", "tegucigalpa"],
        "guatemala": ["guatemala", "guatemalteco"],
        "austria": ["austria", "austriaco", "viena"],
        "bulgaria": ["bulgaria", "bulgaro", "sofia"],
        "croacia": ["croacia", "croata", "zagreb"],
        "bielorrusia": ["bielorrusia", "belarus", "bielorruso", "minsk"],
        "serbia": ["serbia", "serbio", "belgrado"],
        "eslovenia": ["eslovenia", "esloveno", "liubliana"],
        "macedonia": ["macedonia", "macedonio", "skopje"]
    }
    
    for country, keywords in country_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            return country
    return None

def detect_operator(text):
    """Detecta operadora de telecomunicaciones"""
    text_lower = text.lower()
    if "claro" in text_lower:
        return "claro"
    elif "telcel" in text_lower:
        return "telcel"
    elif "a1" in text_lower:
        return "a1"
    return None

def detect_health_topic(text):
    """Detecta tema específico de salud"""
    text_lower = text.lower()
    
    health_topics = {
        "diabetes": ["diabetes", "diabetico", "diabética", "glucosa", "insulina", "azucar en sangre"],
        "obesidad_nutricion": ["obesidad", "sobrepeso", "nutricion", "dieta", "alimentacion", "bajar de peso"],
        "hipertension_corazon": ["hipertension", "presion alta", "corazon", "cardiaco", "cardiovascular"],
        "cancer": ["cancer", "cáncer", "tumor", "oncologia", "oncológico", "mama", "prostata"],
        "salud_mental": ["depresion", "ansiedad", "estres", "mental", "psicologico", "psicológico"],
        "edad": ["niño", "niña", "bebe", "bebé", "adolescente", "adulto", "anciano", "tercera edad"]
    }
    
    for topic, keywords in health_topics.items():
        if any(keyword in text_lower for keyword in keywords):
            return topic
    return None

def detect_education_topic(text):
    """Detecta tema específico de educación"""
    text_lower = text.lower()
    
    education_topics = {
        "digital_tech": ["programacion", "programación", "tecnologia", "tecnología", "digital", "computacion", "computación", "software"],
        "finanzas": ["finanzas", "dinero", "inversion", "inversión", "ahorro", "credito", "crédito"],
        "emprendimiento": ["emprender", "negocio", "empresa", "autoempleo", "emprendedor"],
        "basica": ["primaria", "secundaria", "basica", "básica", "niños", "escolar"],
        "superior": ["universidad", "licenciatura", "carrera", "profesional", "superior"],
        "idiomas": ["ingles", "inglés", "idioma", "lenguaje"],
        "capacitacion": ["curso", "capacitacion", "capacitación", "aprender", "estudiar", "diplomado"]
    }
    
    for topic, keywords in education_topics.items():
        if any(keyword in text_lower for keyword in keywords):
            return topic
    return None

def extract_relevant_urls(prompt):
    """Extrae URLs relevantes basándose en la consulta del usuario"""
    relevant_urls = []
    country = detect_country(prompt)
    operator = detect_operator(prompt)
    health_topic = detect_health_topic(prompt)
    education_topic = detect_education_topic(prompt)
    
    # SALUD
    if health_topic:
        if health_topic == "edad":
            # Agregar todos los manuales por edad
            for age_range, urls in URLS["health"]["manual_por_edad_clikisalud"].items():
                relevant_urls.extend(urls)
        else:
            # Agregar recursos generales de salud
            relevant_urls.extend(URLS["health"]["cuidado_personal_y_profesional"])
            
            # Agregar URLs específicas del tema
            if health_topic in URLS["health"]["prevencion_y_enfermedades"]:
                relevant_urls.extend(URLS["health"]["prevencion_y_enfermedades"][health_topic])
            
            # Agregar cursos relacionados
            relevant_urls.extend(URLS["health"]["cursos_cuidado_salud"][:3])
    
    # EDUCACIÓN
    elif education_topic:
        # Agregar plataforma principal
        relevant_urls.extend(URLS["education_career"]["aprende_org_general"]["principal"])
        relevant_urls.extend(URLS["education_career"]["aprende_org_general"]["areas_principales"])
        
        # URLs específicas por país si aplica
        if country and country in URLS["education_career"]["plataformas_nacionales"]:
            relevant_urls.extend(URLS["education_career"]["plataformas_nacionales"][country])
        
        # URLs específicas por tema
        if education_topic == "digital_tech":
            relevant_urls.extend(URLS["education_career"]["rutas_y_oficios"]["digital_tech"])
        elif education_topic == "finanzas":
            relevant_urls.extend(URLS["education_career"]["rutas_y_oficios"]["administracion_finanzas"])
            relevant_urls.extend(URLS["education_career"]["diplomados_especialidades"]["administracion_finanzas"][:5])
        elif education_topic == "emprendimiento":
            relevant_urls.extend(URLS["education_career"]["diplomados_especialidades"]["autoempleo_negocio"])
        elif education_topic == "basica":
            relevant_urls.extend(URLS["education_career"]["educacion_detallada"]["basica_y_media"])
        elif education_topic == "superior":
            relevant_urls.extend(URLS["education_career"]["educacion_detallada"]["superior"])
    
    # TELECOMUNICACIONES
    elif operator:
        if operator == "telcel":
            relevant_urls.extend(URLS["telcel"])
        elif operator == "claro" and country:
            if country in URLS["claro"]:
                relevant_urls.extend(URLS["claro"][country])
            else:
                # Agregar todas las opciones de Claro si no hay país específico
                for country_urls in URLS["claro"].values():
                    relevant_urls.extend(country_urls)
        elif operator == "a1" and country:
            if country in URLS["a1"]:
                relevant_urls.extend(URLS["a1"][country])
            else:
                # Agregar todas las opciones de A1
                for country_urls in URLS["a1"].values():
                    relevant_urls.extend(country_urls)
    
    return list(set(relevant_urls))  # Eliminar duplicados

def get_context_for_query(prompt):
    """Genera contexto descriptivo y URLs relevantes para la consulta"""
    country = detect_country(prompt)
    operator = detect_operator(prompt)
    health_topic = detect_health_topic(prompt)
    education_topic = detect_education_topic(prompt)
    
    context = []
    
    # SALUD
    if health_topic:
        context.append("📋 ÁREA: SALUD Y BIENESTAR")
        if health_topic == "diabetes":
            context.append("Tema: Diabetes - Prevención, cuidados y manejo de la enfermedad")
        elif health_topic == "obesidad_nutricion":
            context.append("Tema: Obesidad y Nutrición - Alimentación saludable y control de peso")
        elif health_topic == "hipertension_corazon":
            context.append("Tema: Hipertensión y Salud Cardiovascular")
        elif health_topic == "cancer":
            context.append("Tema: Prevención y detección del cáncer")
        elif health_topic == "salud_mental":
            context.append("Tema: Salud Mental - Manejo de estrés, ansiedad y depresión")
        elif health_topic == "edad":
            context.append("Tema: Manuales de salud organizados por grupos de edad")
    
    # EDUCACIÓN
    elif education_topic:
        context.append("📚 ÁREA: EDUCACIÓN Y DESARROLLO PROFESIONAL")
        if education_topic == "digital_tech":
            context.append("Tema: Tecnología y Programación - Cursos de desarrollo digital")
        elif education_topic == "finanzas":
            context.append("Tema: Finanzas Personales - Educación financiera y manejo de dinero")
        elif education_topic == "emprendimiento":
            context.append("Tema: Emprendimiento - Cómo iniciar y gestionar un negocio")
        elif education_topic == "basica":
            context.append("Tema: Educación Básica y Media - Recursos para estudiantes de primaria y secundaria")
        elif education_topic == "superior":
            context.append("Tema: Educación Superior - Cursos universitarios y profesionales")
        elif education_topic == "capacitacion":
            context.append("Tema: Capacitación y Desarrollo de Habilidades")
        
        if country:
            country_names = {
                "el_salvador": "El Salvador",
                "colombia": "Colombia",
                "nicaragua": "Nicaragua",
                "honduras": "Honduras",
                "guatemala": "Guatemala",
                "peru": "Perú"
            }
            if country in country_names:
                context.append(f"País: {country_names[country]} - Plataforma Aprende con Claro disponible")
    
    # TELECOMUNICACIONES
    elif operator:
        context.append("🌐 ÁREA: TELECOMUNICACIONES")
        if operator == "telcel":
            context.append("Operador: Telcel México - Servicios de telefonía móvil")
        elif operator == "claro":
            context.append("Operador: Claro")
            if country:
                country_names = {
                    "argentina": "Argentina",
                    "peru": "Perú",
                    "chile": "Chile"
                }
                if country in country_names:
                    context.append(f"País: {country_names[country]}")
        elif operator == "a1":
            context.append("Operador: A1 Group (Europa)")
            if country:
                country_names = {
                    "austria": "Austria",
                    "bulgaria": "Bulgaria",
                    "croacia": "Croacia",
                    "bielorrusia": "Bielorrusia",
                    "serbia": "Serbia",
                    "eslovenia": "Eslovenia",
                    "macedonia": "Macedonia del Norte"
                }
                if country in country_names:
                    context.append(f"País: {country_names[country]}")
    
    else:
        context.append("ℹ️ Asistente general disponible para Telecomunicaciones, Educación y Salud")
    
    return "\n".join(context) if context else "Información general disponible"

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
        "max_tokens": 2048
    }
    
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

# ==================== ENDPOINTS ====================
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy", 
        "service": "Telecom Copilot API v2.0",
        "ai_ready": client is not None or GROQ_API_KEY is not None,
        "features": ["telecomunicaciones", "educación", "salud"]
    })

@app.route('/chat', methods=['POST'])
def chat():
    """Endpoint principal de chat con contexto mejorado"""
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
        
        # Obtener contexto y URLs relevantes
        context = get_context_for_query(user_message)
        relevant_urls = extract_relevant_urls(user_message)
        
        # Formatear URLs para el prompt
        urls_text = ""
        if relevant_urls:
            urls_text = "Enlaces útiles:\n" + "\n".join([f"- {url}" for url in relevant_urls[:10]])  # Limitar a 10 URLs
        else:
            urls_text = "Explora nuestras áreas: Telecomunicaciones, Educación (aprende.org) y Salud (clikisalud.net)"
        
        # Preparar mensajes para Groq
        formatted_prompt = SYSTEM_PROMPT.format(context=context, urls=urls_text)
        
        messages = [
            {"role": "system", "content": formatted_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # Llamar a Groq
        if client and client != "api_fallback":
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.7,
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
            "relevant_urls": relevant_urls[:5]  # Devolver las 5 URLs más relevantes
        })
        
    except Exception as e:
        logger.error(f"Error en /chat: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

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
        
        relevant_urls = extract_relevant_urls(query)
        context = get_context_for_query(query)
        
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
        if path.startswith('styles/'):
            with open(f'../frontend/{path}', 'r', encoding='utf-8') as f:
                return f.read(), 200, {'Content-Type': 'text/css'}
        elif path.startswith('js/'):
            with open(f'../frontend/{path}', 'r', encoding='utf-8') as f:
                return f.read(), 200, {'Content-Type': 'application/javascript'}
        else:
            with open(f'../frontend/{path}', 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        return f"Archivo no encontrado: {path}", 404

if __name__ == '__main__':
    logger.info(f"🚀 Iniciando Telecom Copilot v2.0 en http://localhost:{PORT}")
    logger.info("📚 Áreas disponibles: Telecomunicaciones | Educación | Salud")
    app.run(host='0.0.0.0', port=PORT, debug=False)
