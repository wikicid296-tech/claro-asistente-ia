import os
import logging
from groq import Groq
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import asyncio
import aiohttp
from typing import List
import re

# Configuración
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URLs Configuration (tu configuración original)
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

# Initialize Groq client
try:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
except Exception as e:
    logger.error(f"Error initializing Groq client: {str(e)}")
    client = None

# Función mejorada para extraer texto de páginas web
async def fetch_url(session, url):
    """Obtiene contenido de una URL de forma asíncrona"""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Remover scripts y styles
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Extraer texto de elementos importantes
                text_elements = []
                
                # Títulos
                for tag in ['h1', 'h2', 'h3']:
                    elements = soup.find_all(tag)
                    for element in elements:
                        text = element.get_text().strip()
                        if text and len(text) > 5:
                            text_elements.append(f"## {text}")
                
                # Párrafos y listas
                for tag in ['p', 'li']:
                    elements = soup.find_all(tag)
                    for element in elements:
                        text = element.get_text().strip()
                        if text and len(text) > 20 and len(text) < 500:
                            text_elements.append(text)
                
                content = '\n'.join(text_elements[:15])  # Limitar a 15 elementos
                return f"=== CONTENIDO DE {url} ===\n{content}\n"
                
    except Exception as e:
        logger.error(f"Error fetching {url}: {str(e)}")
        return None

async def load_web_content_async(urls):
    """Carga contenido web de forma asíncrona"""
    try:
        if not urls:
            return ""
        
        async with aiohttp.ClientSession() as session:
            tasks = [fetch_url(session, url) for url in urls[:3]]  # Máximo 3 URLs
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
        # Filtrar resultados exitosos
        valid_results = [r for r in results if r and not isinstance(r, Exception)]
        return '\n'.join(valid_results)
        
    except Exception as e:
        logger.error(f"Error in load_web_content_async: {str(e)}")
        return ""

# Funciones de detección (simplificadas)
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
    """Detecta operadora en el texto"""
    text_lower = text.lower()
    if "claro" in text_lower:
        return "claro"
    elif "telcel" in text_lower:
        return "telcel"
    elif "a1" in text_lower or "a one" in text_lower:
        return "a1"
    return None

def detect_topic(text):
    """Detecta tema en el texto"""
    text_lower = text.lower()
    
    health_words = ["salud", "medico", "hospital", "doctor", "enfermedad", "tratamiento"]
    education_words = ["educacion", "curso", "aprender", "estudiar", "clase", "capacitacion"]
    
    if any(word in text_lower for word in health_words):
        return "health"
    elif any(word in text_lower for word in education_words):
        return "education"
    return None

def get_relevant_urls(prompt):
    """Obtiene URLs relevantes basadas en el prompt"""
    country = detect_country(prompt)
    operator = detect_operator(prompt)
    topic = detect_topic(prompt)
    
    urls = []
    
    # Prioridad 1: Salud o Educación
    if topic and topic in URLS:
        urls.extend(URLS[topic][:2])  # Primeras 2 URLs del tema
    
    # Prioridad 2: Telecomunicaciones
    elif operator == "telcel" or country == "mexico":
        urls.extend(URLS["telcel"])
    elif operator == "claro" and country and country in URLS["claro"]:
        urls.extend(URLS["claro"][country][:2])
    elif operator == "a1" and country and country in URLS["a1"]:
        urls.extend(URLS["a1"][country][:1])
    
    # Fallback
    if not urls:
        urls.extend(URLS["telcel"])  # Telcel como fallback
    
    return urls

# System prompt mejorado
SYSTEM_PROMPT = """Eres un asistente especializado en servicios de telecomunicaciones, salud y educación.

CONTEXTO DISPONIBLE:
{context}

INSTRUCCIONES:
1. Usa SOLO la información del contexto proporcionado
2. Si el contexto habla de salud, enfócate en servicios médicos y aclarar que no reemplaza consulta profesional
3. Si el contexto habla de educación, describe cursos y programas disponibles
4. Si el contexto habla de telecomunicaciones, proporciona información específica de planes y servicios
5. Sé conciso, útil y profesional
6. Si no hay información relevante en el contexto, sugiere reformular la pregunta

Responde en español de manera clara y organizada."""

# Función principal de procesamiento
async def process_chat_message(message: str, action: str = None):
    """Procesa un mensaje del chat de forma asíncrona"""
    try:
        if not client:
            return "⚠️ El servicio de IA no está disponible. Por favor, verifica la configuración de GROQ_API_KEY."
        
        logger.info(f"Procesando mensaje: {message}")
        
        # Obtener URLs relevantes
        relevant_urls = get_relevant_urls(message)
        logger.info(f"URLs relevantes: {relevant_urls}")
        
        # Cargar contenido web
        context = await load_web_content_async(relevant_urls)
        if not context:
            context = "No se pudo cargar información específica del contexto en este momento."
        
        logger.info(f"Contexto cargado: {len(context)} caracteres")
        
        # Preparar mensaje para Groq
        formatted_prompt = SYSTEM_PROMPT.format(context=context)
        
        messages = [
            {"role": "system", "content": formatted_prompt},
            {"role": "user", "content": message}
        ]
        
        # Llamar a Groq
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
            stream=False
        )
        
        response = completion.choices[0].message.content
        logger.info("Respuesta generada exitosamente")
        return response
        
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        return f"❌ Error al procesar tu mensaje. Por favor, intenta de nuevo. Error: {str(e)}"