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
from prompts import URLS, SYSTEM_PROMPT, SMS_SYSTEM_PROMPT,RCS_SYSTEM_PROMPT,WHATSAPP_SYSTEM_PROMPT

load_dotenv()

app = Flask(__name__)
CORS(app)
app.register_blueprint(calendar_bp)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ AHORA SÍ IMPORTAR CON LOGGER DISPONIBLE
try:
    from aprende_ia_model_api import ask_about_vector_store
    aprende_ia_available = True
    logger.info("✅ Módulo de Aprende.org IA cargado correctamente")
except Exception as e:
    aprende_ia_available = False
    logger.warning(f"⚠️ Módulo de Aprende.org IA no disponible: {str(e)}")

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
    current_context = detect_main_topic(current_message)
    previous_contexts = [detect_main_topic(msg) for msg in previous_messages]
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
    telecom_keywords = ['claro', 'telcel', 'Telcel', 'a1', 'plan', 'internet', 'telefon', 'móvil', 'movil', 
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
    mem = CHAT_MEMORY.get(user_key, [])
    if not mem:
        return []
    if detect_context_change(current_message, mem):
        logger.info(f"🧹 Limpiando memoria anterior por cambio de contexto")
        CHAT_MEMORY[user_key] = []  # Limpiar memoria
        return []
    return mem[-1:] if mem else []

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

# ==================== NUEVAS FUNCIONES PARA APRENDE IA ====================

def should_use_aprende_ia(message, current_mode):
    """
    Determina si debe usar el modelo especializado de Aprende.org
    
    Returns: bool
    """
    # 🆕 LOG 1: Verificar que la función se ejecuta
    logger.info(f"🔍 Verificando Aprende IA - Modo: '{current_mode}', Módulo disponible: {aprende_ia_available}")
    
    if not aprende_ia_available:
        logger.warning("⚠️ Módulo Aprende IA no disponible")
        return False
    
    # Solo usar si el modo actual es 'aprende'
    if current_mode != 'aprende':
        logger.info(f"⏭️ Modo '{current_mode}' no es 'aprende', saltando Aprende IA")
        return False
    
    message_lower = message.lower()
    
    # Palabras clave que indican búsqueda de cursos/recursos
    aprende_keywords = [
        'curso', 'cursos', 'aprender', 'estudiar', 'capacitación', 'capacitacion',
        'diplomado', 'especialidad', 'ruta', 'aprende.org', 'aprende',
        'enseñar', 'educación', 'educacion', 'formación', 'formacion', 
        'certificado', 'programa', 'clase', 'aprendizaje'
    ]
    
    # Si contiene alguna palabra clave, usar Aprende IA
    has_keyword = any(keyword in message_lower for keyword in aprende_keywords)
    
    # 🆕 LOG 2: Verificar detección de palabras clave
    if has_keyword:
        logger.info(f"✅ Palabras clave DETECTADAS en: '{message[:50]}...'")
    else:
        logger.warning(f"❌ NO se detectaron palabras clave en: '{message[:50]}...'")
    
    return has_keyword


def detect_resource_type(url):
    """
    Detecta el tipo de recurso basándose en la URL
    Returns: 'curso', 'diplomado', 'ruta', 'especialidad', 'webpage'
    """
    if not url:
        return 'general'
    
    url_lower = url.lower()
    
    if '/cursos/' in url_lower or '/curso/' in url_lower:
        return 'curso'
    elif '/diplomado/' in url_lower:
        return 'diplomado'
    elif '/ruta/' in url_lower:
        return 'ruta'
    elif '/especialidad/' in url_lower:
        return 'especialidad'
    else:
        return 'webpage'

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
        current_mode = data.get('action', 'busqueda')
        
        # 🆕 LOGS PARA DEBUGGING
        logger.info("="*50)
        logger.info(f"📨 Mensaje recibido: '{user_message[:100]}'")
        logger.info(f"📊 Modo recibido del frontend: '{current_mode}'")
        logger.info(f"🔧 Aprende IA disponible: {aprende_ia_available}")
        logger.info("="*50)
        
        if not user_message:
            return jsonify({"success": False, "error": "Mensaje vacío"}), 400
        
        # 🆕 NUEVA LÓGICA: Detectar si usar Aprende IA
        use_aprende = should_use_aprende_ia(user_message, current_mode)
        logger.info(f"🎯 Resultado should_use_aprende_ia: {use_aprende}")
        
        if use_aprende:
            try:
                logger.info(f"🎓 Usando Aprende IA para: {user_message[:50]}...")
                resultado = ask_about_vector_store(user_message)
                
                logger.info(f"✅ Respuesta de Aprende IA recibida")
                logger.info(f"📍 URL recurso: {resultado.get('url_recurso', 'Sin URL')}")
                logger.info(f"🎥 URL video: {resultado.get('url_video', 'Sin video')}")
                logger.info(f"📄 URL PDF: {resultado.get('url_pdf', 'Sin PDF')}")
                logger.info(f"📦 Tipo contenido: {resultado.get('tipo_contenido', 'webpage')}")
                
                return jsonify({
                    "success": True,
                    "response": resultado["respuesta"],
                    "url_recurso": resultado["url_recurso"],
                    "url_video": resultado.get("url_video", ""),
                    "url_pdf": resultado.get("url_pdf", ""),
                    "tipo_contenido": resultado.get("tipo_contenido", "webpage"),
                    "tipo_recurso": resultado.get("tipo_recurso", "curso"),
                    "context": "📚 ÁREA: EDUCACIÓN Y DESARROLLO PROFESIONAL (Aprende.org)",
                    "relevant_urls": [resultado["url_recurso"]] if resultado["url_recurso"] else [],
                    "memory_used": 0,
                    "context_reset": False,
                    "aprende_ia_used": True
                })
            except Exception as e:
                logger.error(f"❌ Error en Aprende IA: {str(e)}")
                logger.info("↩️ Fallback a Groq API")
        
        # 🔄 FLUJO ORIGINAL (Groq)
        logger.info("📡 Usando Groq API (flujo normal)")
        
        try:
            user_key = _get_user_key()
            prev_messages = get_relevant_memory(user_key, user_message)
        except Exception:
            prev_messages = []
            user_key = None
        
        try:
            if user_key is not None:
                mem = CHAT_MEMORY.get(user_key, [])
                mem.append(user_message)
                if len(mem) > 2:
                    mem = mem[-2:]
                CHAT_MEMORY[user_key] = mem
        except Exception:
            pass
        
        context = safe_get_context_for_query(user_message)
        relevant_urls = safe_extract_relevant_urls(user_message)
        
        urls_text = ""
        if relevant_urls:
            urls_text = "Enlaces útiles:\n" + "\n".join([f"- {url}" for url in relevant_urls[:5]])
        else:
            urls_text = "Explora: aprende.org | clikisalud.net"
        
        try:
            formatted_prompt = SYSTEM_PROMPT.format(context=context, urls=urls_text)
        except Exception:
            formatted_prompt = f"Eres un asistente. Contexto:\n{context}\n\n{urls_text}"
        
        messages = [{"role": "system", "content": formatted_prompt}]
        
        for pm in prev_messages:
            if pm and pm.strip() and pm.strip() != user_message.strip():
                messages.append({"role": "user", "content": pm})
        
        messages.append({"role": "user", "content": user_message})
        
        logger.info(f"📊 Mensajes enviados a Groq: {len(messages)}")
        
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
            "context_reset": len(prev_messages) == 0
        })
        
    except Exception as e:
        logger.error(f"❌ Error en /chat: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
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
    """Endpoint SMS optimizado con límite estricto de caracteres"""
    try:
        incoming_msg = request.values.get('Body', '').strip()
        from_number = request.values.get('From', '')
        if not incoming_msg:
            resp = MessagingResponse()
            resp.message("Mensaje invalido")
            return str(resp)
        
        # 🆕 MEJORA 1: Log para debugging
        logger.info(f"SMS recibido de {from_number}: {incoming_msg[:50]}")
        
        # Memoria inteligente (sin cambios)
        user_key = from_number
        prev_messages = get_relevant_memory(user_key, incoming_msg)
        
        # Actualizar memoria (sin cambios)
        mem = CHAT_MEMORY.get(user_key, [])
        mem.append(incoming_msg)
        if len(mem) > 2:
            mem = mem[-2:]
        CHAT_MEMORY[user_key] = mem
        
        # Contexto (sin cambios)
        context = safe_get_context_for_query(incoming_msg)
        relevant_urls = safe_extract_relevant_urls(incoming_msg)
        
        # 🆕 MEJORA 2: URLs ultra cortas solo si son críticas
        urls_text = ""
        if relevant_urls and len(relevant_urls) > 0:
            # Solo incluir dominio principal si cabe
            first_url = relevant_urls[0].split('/')[2] if '/' in relevant_urls[0] else relevant_urls[0]
            urls_text = first_url[:20]  # Solo dominio, máximo 20 chars
        
        # 🆕 MEJORA 3: Prompt reformateado para forzar brevedad
        try:
            formatted_prompt = SMS_SYSTEM_PROMPT.format(
                context=context[:50],  # Limitar contexto también
                urls=urls_text
            )
        except Exception:
            formatted_prompt = "Asistente SMS. Max 140 caracteres. Sé breve."
        
        # 🆕 MEJORA 4: Simplificar mensajes (menos contexto histórico)
        messages = [{"role": "system", "content": formatted_prompt}]
        
        # Solo incluir UN mensaje previo si es muy relevante
        if prev_messages and len(prev_messages) > 0:
            last_msg = prev_messages[-1][:50]  # Truncar mensaje anterior
            messages.append({"role": "user", "content": last_msg})
        
        messages.append({"role": "user", "content": incoming_msg})
        
        # 🆕 MEJORA 5: Configuración optimizada para Groq
        if client and client != "api_fallback":
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.5,  # 🆕 Reducir para respuestas más directas
                max_tokens=50,    # 🆕 CRÍTICO: Máximo 40 tokens (~140 chars)
                top_p=0.9,        # 🆕 Limitar creatividad
                frequency_penalty=0.5  # 🆕 Evitar repeticiones
            )
            ai_response = completion.choices[0].message.content
        else:
            # Llamada directa a API con parámetros ajustados
            result = call_groq_api_directly_sms(messages, max_tokens=40)
            ai_response = result["choices"][0]["message"]["content"]
        
        # 🆕 MEJORA 6: Limpieza y truncado agresivo
        # Eliminar saltos de línea y espacios extra
        ai_response = ' '.join(ai_response.split())
        
        # 🆕 MEJORA 7: Truncado con margen de seguridad
        MAX_SMS_LENGTH = 140  # Más conservador que 160
        
        if len(ai_response) > MAX_SMS_LENGTH:
            # Buscar último espacio antes del límite para no cortar palabras
            cutoff = ai_response[:MAX_SMS_LENGTH-3].rfind(' ')
            if cutoff > 0:
                ai_response = ai_response[:cutoff] + "..."
            else:
                ai_response = ai_response[:MAX_SMS_LENGTH-3] + "..."
        
        # 🆕 MEJORA 8: Log de respuesta para monitoreo
        logger.info(f"SMS respuesta ({len(ai_response)} chars): {ai_response}")
        
        # Enviar respuesta
        resp = MessagingResponse()
        resp.message(ai_response)
        return str(resp), 200, {'Content-Type': 'text/xml'}
        
    except Exception as e:
        logger.error(f"Error en /sms: {str(e)}")
        # 🆕 MEJORA 9: Mensaje de error aún más corto
        resp = MessagingResponse()
        resp.message("Error. Reintentar")  # Solo 17 caracteres
        return str(resp), 200, {'Content-Type': 'text/xml'}


# 🆕 FUNCIÓN AUXILIAR NUEVA para llamadas directas a API con límite SMS
def call_groq_api_directly_sms(messages, max_tokens=40):
    """Versión especial para SMS con límites estrictos"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": max_tokens,
        "top_p": 0.9,
        "frequency_penalty": 0.5
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()


# ==================== ENDPOINT RCS (NUEVO) ====================
@app.route('/rcs', methods=['POST', 'GET'])
@limiter.limit("20 per minute")
@limiter.limit("1 per 2 seconds")
def rcs_webhook():
    """Endpoint RCS con logging mejorado"""
    try:
        # Log del método HTTP
        logger.info(f"=== RCS REQUEST ===")
        logger.info(f"Method: {request.method}")
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"Headers: {dict(request.headers)}")
        
        # Manejar GET (para verificación de Twilio)
        if request.method == 'GET':
            logger.info("GET request recibido - probablemente verificación de webhook")
            return "RCS Webhook activo", 200
        
        # Extraer datos del mensaje
        if request.is_json:
            data = request.get_json()
            logger.info(f"JSON data: {data}")
            incoming_msg = data.get('Body', '').strip()
            from_number = data.get('From', '')
        else:
            logger.info(f"Form data: {request.values}")
            incoming_msg = request.values.get('Body', '').strip()
            from_number = request.values.get('From', '')
        
        logger.info(f"📱 RCS de {from_number}: {incoming_msg}")
        
        # Validación
        if not incoming_msg:
            logger.warning("Mensaje vacío recibido")
            resp = MessagingResponse()
            resp.message("Por favor envía un mensaje válido.")
            return str(resp), 200, {'Content-Type': 'text/xml'}
        
        # Memoria inteligente
        user_key = from_number
        prev_messages = get_relevant_memory(user_key, incoming_msg)
        
        # Actualizar memoria
        mem = CHAT_MEMORY.get(user_key, [])
        mem.append(incoming_msg)
        if len(mem) > 2:
            mem = mem[-2:]
        CHAT_MEMORY[user_key] = mem
        
        # Contexto
        context = safe_get_context_for_query(incoming_msg)
        relevant_urls = safe_extract_relevant_urls(incoming_msg)
        
        # URLs para RCS
        urls_text = ""
        if relevant_urls:
            urls_text = "\n\n📎 *Enlaces útiles:*\n" + "\n".join([f"• {url}" for url in relevant_urls[:3]])
        
        # Prompt
        try:
            formatted_prompt = RCS_SYSTEM_PROMPT.format(context=context, urls=urls_text)
        except Exception as e:
            logger.error(f"Error formateando prompt: {e}")
            formatted_prompt = f"Asistente RCS.\n{context}\n{urls_text}"
        
        # Construir mensajes
        messages = [{"role": "system", "content": formatted_prompt}]
        
        for pm in prev_messages:
            if pm and pm.strip():
                messages.append({"role": "user", "content": pm})
        
        messages.append({"role": "user", "content": incoming_msg})
        
        # Llamar a Groq
        logger.info("Llamando a Groq API...")
        if client and client != "api_fallback":
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.5,
                max_tokens=500
            )
            ai_response = completion.choices[0].message.content
        else:
            result = call_groq_api_directly(messages)
            ai_response = result["choices"][0]["message"]["content"]
        
        # Limitar longitud
        if len(ai_response) > 1000:
            ai_response = ai_response[:997] + "..."
        
        logger.info(f"✅ RCS respuesta ({len(ai_response)} chars): {ai_response[:100]}")
        
        # Enviar respuesta
        resp = MessagingResponse()
        resp.message(ai_response)
        
        response_xml = str(resp)
        logger.info(f"Response XML: {response_xml}")
        
        return response_xml, 200, {'Content-Type': 'text/xml'}
        
    except Exception as e:
        logger.error(f"❌ Error en /rcs: {str(e)}", exc_info=True)
        resp = MessagingResponse()
        resp.message("❌ Error al procesar mensaje. Intenta nuevamente.")
        return str(resp), 200, {'Content-Type': 'text/xml'}


# ==================== ENDPOINT STATUS CALLBACK (OPCIONAL) ====================
@app.route('/rcs/status', methods=['POST'])
@limiter.exempt
def rcs_status_callback():
    """Recibe actualizaciones de estado de mensajes RCS"""
    try:
        message_sid = request.values.get('MessageSid')
        message_status = request.values.get('MessageStatus')
        to_number = request.values.get('To')
        from_number = request.values.get('From')
        error_code = request.values.get('ErrorCode')
        
        logger.info(f"📊 RCS Status Update:")
        logger.info(f"   MessageSid: {message_sid}")
        logger.info(f"   Status: {message_status}")
        logger.info(f"   To: {to_number}")
        logger.info(f"   From: {from_number}")
        
        if error_code:
            logger.error(f"   Error Code: {error_code}")
        
        return '', 200
        
    except Exception as e:
        logger.error(f"Error en /rcs/status: {str(e)}")
        return '', 200
        

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