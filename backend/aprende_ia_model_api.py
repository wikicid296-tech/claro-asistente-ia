from dotenv import load_dotenv
from openai import OpenAI
import os
import re
import asyncio
from playwright.async_api import async_playwright
import logging
import sys
sys.path.insert(0, os.path.dirname(__file__))

# Precios de OpenAI (duplicados aquí por si acaso)
OPENAI_PRICES = {
    "input": 2.50,
    "output": 10.00
}

def calculate_openai_cost(input_tokens, output_tokens):
    """Calcula costo de OpenAI localmente"""
    input_cost = (input_tokens / 1_000_000) * OPENAI_PRICES["input"]
    output_cost = (output_tokens / 1_000_000) * OPENAI_PRICES["output"]
    return input_cost + output_cost

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
vector_store_id = os.getenv("VECTOR_STORE_ID")

# 🆕 FILTRO DE RELEVANCIA - FUNCIÓN NUEVA
def es_pregunta_educativa(question: str) -> bool:
    """
    Determina si la pregunta es realmente sobre temas educativos 
    que justifiquen buscar en Aprende.org
    """
    question_lower = question.lower()
    
    # PALABRAS CLAVE EDUCATIVAS (temas relevantes para Aprende.org)
    temas_educativos = [
        # Cursos y educación
        'curso', 'cursos', 'aprender', 'estudiar', 'educación', 'educacion', 
        'capacitación', 'capacitacion', 'formación', 'formacion', 'diplomado',
        'carrera', 'profesional', 'técnico', 'tecnico', 'habilidad', 'habilidades',
        'aprende.org', 'capacitate', 'clikisalud', 'capacítate',
        
        # Áreas de conocimiento específicas
        'programación', 'programacion', 'inglés', 'ingles', 'matemática', 'matematica',
        'ciencia', 'tecnología', 'tecnologia', 'digital', 'computación', 'computacion',
        'salud', 'medicina', 'nutrición', 'nutricion', 'ejercicio', 'bienestar',
        'finanzas', 'contabilidad', 'administración', 'administracion', 'negocios',
        'emprendimiento', 'marketing', 'ventas', 'liderazgo', 'trabajo en equipo',
        'idioma', 'idiomas', 'oficio', 'oficios', 'taller', 'talleres',
        
        # Verbos de aprendizaje
        'enseñar', 'ensenar', 'instruir', 'capacitar', 'formar', 'preparar',
        'desarrollar', 'mejorar', 'perfeccionar', 'aprendo', 'estudio',
        
        # Temas específicos de cursos
        'excel', 'word', 'powerpoint', 'office', 'programar', 'código', 'codigo',
        'web', 'página web', 'pagina web', 'diseño', 'diseno', 'photoshop',
        'contabilidad', 'financiero', 'impuesto', 'impuestos', 'fiscal',
        'recursos humanos', 'rrhh', 'selección', 'seleccion', 'personal',
        'venta', 'comercial', 'cliente', 'clientes', 'atención al cliente',
        'electricidad', 'electricista', 'plomería', 'plomeria', 'albañil', 'albanil',
        'cocina', 'chef', 'repostería', 'reposteria', 'panadería', 'panaderia'
    ]
    
    # PALABRAS CLAVE NO EDUCATIVAS (temas que NO deben usar Aprende.org)
    temas_no_educativos = [
        # Entretenimiento y famosos
        'tailor swift', 'taylor swift', 'novio', 'novia', 'famoso', 'famosos',
        'celebridad', 'celebridades', 'actor', 'actriz', 'cantante', 'música',
        'película', 'pelicula', 'serie', 'deporte', 'deportes', 'fútbol', 'futbol',
        'baloncesto', 'deportivo', 'artista', 'banda', 'grupo musical',
        
        # Preguntas personales/generales
        'quién es', 'quien es', 'qué es', 'que es', 'cómo es', 'como es',
        'cuándo', 'cuando', 'dónde', 'donde', 'por qué', 'porque',
        'cuánto', 'cuanto', 'cuál', 'cual', 'cuáles', 'cuales',
        
        # Noticias y eventos actuales
        'noticia', 'noticias', 'actualidad', 'política', 'politica', 'evento',
        'elección', 'eleccion', 'presidente', 'gobierno', 'ley', 'legal',
        
        # Preguntas generales de conocimiento
        'historia de', 'biografía', 'biografia', 'quién inventó', 'quien invento',
        'qué pasó', 'que paso', 'significado de', 'definición', 'definicion',
        
        # Entretenimiento y cultura pop
        'videojuego', 'videojuegos', 'juego', 'juegos', 'anime', 'manga',
        'comics', 'cómic', 'comic', 'película', 'cine', 'televisión', 'television',
        
        # Preguntas personales
        'edad de', 'años de', 'cumpleaños', 'nacimiento', 'murió', 'muriò', 'muerto'
    ]
    
    # Verificar si contiene temas NO educativos
    for tema in temas_no_educativos:
        if tema in question_lower:
            logger.info(f"❌ Pregunta rechazada - Contiene tema no educativo: '{tema}'")
            return False
    
    # Verificar si contiene temas educativos
    for tema in temas_educativos:
        if tema in question_lower:
            logger.info(f"✅ Pregunta aceptada - Contiene tema educativo: '{tema}'")
            return True
    
    # Si no coincide con nada, por defecto NO usar Aprende.org
    logger.info("❌ Pregunta rechazada - No contiene temas educativos relevantes")
    return False


async def extraer_contenido_multimedia(resource_url: str) -> dict:
    """
    Extrae contenido multimedia usando Playwright (compatible con Render Starter)
    """
    logger.info(f"🔍 Accediendo a: {resource_url}")
    
    async with async_playwright() as p:
        browser = None
        try:
            # Lanzar navegador headless
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                ]
            )
            page = await browser.new_page()
            
            # Navegar a la URL
            logger.info("📡 Navegando a la página...")
            await page.goto(resource_url, wait_until="networkidle", timeout=30000)
            logger.info(f"✅ Página cargada exitosamente")
            
            # Esperar contenido dinámico
            await page.wait_for_timeout(3000)
            
            # Obtener HTML
            html = await page.content()
            logger.info(f"📄 HTML obtenido. Longitud: {len(html)} caracteres")
            
            # ============ BUSCAR VIDEOS EN ELEMENTOS DOM ============
            logger.info("🎥 Buscando videos en elementos DOM...")
            
            video_element = await page.query_selector('video')
            if video_element:
                logger.info("✅ Encontrado elemento <video>")
                
                video_src = await video_element.get_attribute('src')
                if video_src:
                    logger.info(f"✅ Video en atributo src: {video_src}")
                    await browser.close()
                    return {"tipo": "video", "url": video_src}
                
                sources = await video_element.query_selector_all('source')
                for source in sources:
                    src = await source.get_attribute('src')
                    if src:
                        logger.info(f"✅ Video en <source>: {src}")
                        await browser.close()
                        return {"tipo": "video", "url": src}
            
            # ============ BUSCAR VIDEOS CON REGEX ============
            logger.info("🔍 Buscando videos con regex...")
            
            video_patterns = {
                'mp4_directo': r'https://[^\s\'"<>]+\.mp4(?:\?[^\s\'"<>]*)?',
                'm3u8_streaming': r'https://[^\s\'"<>]+\.m3u8(?:\?[^\s\'"<>]*)?',
            }
            
            for nombre_patron, patron in video_patterns.items():
                match = re.search(patron, html, re.IGNORECASE)
                if match:
                    url_video = match.group(0)
                    logger.info(f"✅ Video encontrado ({nombre_patron}): {url_video}")
                    await browser.close()
                    return {"tipo": "video", "url": url_video}
            
            logger.info("❌ No se encontraron videos")
            
            # ============ BUSCAR PDFs ============
            logger.info("📄 Buscando PDFs...")
            
            pdf_pattern = r'https://[^\s\'"<>]+\.pdf(?:\?[^\s\'"<>]*)?'
            match = re.search(pdf_pattern, html, re.IGNORECASE)
            if match:
                url_pdf = match.group(0)
                logger.info(f"✅ PDF encontrado: {url_pdf}")
                await browser.close()
                return {"tipo": "pdf", "url": url_pdf}
            
            logger.info("📋 Usando página completa")
            await browser.close()
            return {"tipo": "webpage", "url": resource_url}
            
        except Exception as e:
            logger.error(f"💥 Error: {str(e)}")
            if browser:
                await browser.close()
            return {"tipo": "webpage", "url": resource_url}


def detectar_tipo_recurso(url: str) -> str:
    """Detecta el tipo de recurso según la URL"""
    url_lower = url.lower()
    if '/cursos/' in url_lower or '/curso/' in url_lower:
        return 'curso'
    elif '/diplomado/' in url_lower:
        return 'diplomado'
    elif '/ruta/' in url_lower:
        return 'ruta'
    elif '/especialidad/' in url_lower:
        return 'especialidad'
    return 'general'


def ask_about_vector_store(question: str) -> dict:
    """
    Función principal MODIFICADA con filtro de relevancia
    para consultar el vector store de Aprende.org
    """
    logger.info(f"🤖 Pregunta recibida: {question}")
    
    # 🆕 FILTRO DE RELEVANCIA - Verificar si es pregunta educativa
    if not es_pregunta_educativa(question):
        logger.info("❌ Pregunta NO relevante para Aprende.org - Usando respuesta general")
        return {
            "respuesta": f"🤔 Veo que tu pregunta está relacionada con '{question}'. Me especializo en ayudarte con **cursos, capacitación y desarrollo profesional** de Aprende.org.\n\n💡 **¿Te gustaría buscar algún curso específico o aprender alguna habilidad nueva?** Por ejemplo, puedo ayudarte con:\n• Cursos de programación y tecnología\n• Capacitación en habilidades profesionales\n• Desarrollo personal y bienestar\n• Cursos técnicos y oficios\n\n¡Cuéntame qué te gustaría aprender! 📚",
            "url_recurso": "",
            "url_video": "",
            "url_pdf": "",
            "tipo_contenido": "general",
            "tipo_recurso": "general"
        }
    
    try:
        logger.info("✅ Pregunta relevante - Consultando vector store de OpenAI...")
        
        response = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {
                    "role": "system",
                    "content": (
                        "Eres Claria un asistente experto en capacitación profesional e identificación de recursos de aprendizaje adecuados disponibles en la plataforma Aprende.org"
                        "Tu tarea es recomendar recursos y cursos útiles al usuario basándote en su pregunta, además de respoder a posibles dudas que pueda tener."
                        "siempre incluye una URL directa al recurso o curso que recomiendas, si es una duda del usuario, responde su duda y suguiere un recurso relacionado. INDICA NOMBRE DEL CURSO AL QUE PERTENECE Y NOMBRE DEL RECURSO."
                        "Mantén un tono cordial, amigable y accesible. Nunca respondas con una pregunta para el usuario"
                        "NO MENCIONES: He visto que has subido algunos archivos. MENCIONA EN SU LUGAR QUE SON RECURSOS disponibles en Aprende.org."
                        "SI EL USUARIO HACE UNA PETICIÓN DE TIPO TUTORIAL (cómo hacer algo), DEBES: 1) Responder brevemente con tu conocimiento sobre cómo hacerlo (2-3 pasos máximo). 2) BUSCAR en el vector store el curso más relevante usando palabras clave del tema. 3) INCLUIR OBLIGATORIAMENTE la URL completa del curso encontrado (https://aprende.org/cursos/XXX?resourceId=YYY). 4) Mencionar el nombre exacto del curso (courseName) tal como aparece en la base de datos. NUNCA inventes nombres de cursos ni URLs. Si no encuentras un curso específico, busca el más cercano temáticamente. EJEMPLO: Usuario: '¿cómo cambiar un foco?' → Respuesta: 'Para cambiar un foco: 1) Apaga el interruptor, 2) Desenrosca el foco viejo, 3) Enrosca el nuevo. Te recomiendo el curso \"Electricista\" de Aprende donde aprenderás instalaciones eléctricas básicas en el recurso Instalación eléctrica en casas: https://aprende.org/cursos/367?resourceId=11563' - SIEMPRE incluye la URL del curso, no solo la página principal de Aprende"
                    )
                },
                {"role": "user", "content": question}
            ],
            tools=[{
                "type": "file_search",
                "vector_store_ids": [vector_store_id],
                "max_num_results": 7
            }]
        )

        texto_respuesta = response.output_text.strip()
        logger.info(f"💬 Respuesta generada ({len(texto_respuesta)} caracteres)")

        # 🆕 TRACKEAR TOKENS DE OPENAI
        try:
            # Intentar extraer usage de diferentes formas según la API de OpenAI
            usage = None
            
            # Forma 1: Atributo directo
            if hasattr(response, 'usage'):
                usage = response.usage
            
            # Forma 2: En metadata
            elif hasattr(response, 'metadata') and hasattr(response.metadata, 'usage'):
                usage = response.metadata.usage
            
            # Forma 3: Método get (si es dict-like)
            elif hasattr(response, 'get'):
                usage = response.get('usage')
            
            if usage:
                input_tokens = getattr(usage, 'input_tokens', 0) or getattr(usage, 'prompt_tokens', 0)
                output_tokens = getattr(usage, 'output_tokens', 0) or getattr(usage, 'completion_tokens', 0)
                
                if input_tokens > 0 or output_tokens > 0:
                    cost = calculate_openai_cost(input_tokens, output_tokens)
                    logger.info(f"📊 OpenAI Tokens: {input_tokens} in + {output_tokens} out | Costo: ${cost:.6f}")
                    
                    # Intentar actualizar el consumo global
                    try:
                        from flask_app import add_usage
                        add_usage(cost)
                    except ImportError:
                        logger.warning("⚠️ No se pudo importar add_usage, guardando costo localmente")
                        # Guardar en variable de entorno directamente
                        current = float(os.getenv("USAGE_CONSUMED", "0.00"))
                        new_total = current + cost
                        os.environ["USAGE_CONSUMED"] = str(round(new_total, 4))
                        logger.info(f"💸 Costo OpenAI agregado: ${cost:.6f} | Total: ${new_total:.4f}")
                else:
                    logger.warning("⚠️ No se encontraron tokens en usage de OpenAI")
            else:
                logger.warning("⚠️ No se pudo extraer usage de la respuesta de OpenAI")
                
        except Exception as e:
            logger.error(f"❌ Error trackeando tokens de OpenAI: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Extraer URL del recurso
        logger.info("🔗 Extrayendo URL del recurso...")
        patron_url = r'https?://[^\s\)\]\}\>\,\;\"\']+'
        coincidencias = re.findall(patron_url, texto_respuesta)
        urls_aprende = [url for url in coincidencias if 'aprende.org' in url.lower()]
        url_recurso = urls_aprende[0] if urls_aprende else ""
        
        if url_recurso:
            logger.info(f"✅ URL encontrada: {url_recurso}")
        else:
            logger.warning("⚠️ No se encontró URL en la respuesta, intentando backup...")
            # Fallback: Buscar en anotaciones de file_search
            try:
                if hasattr(response, 'annotations') and response.annotations:
                    for annotation in response.annotations:
                        if hasattr(annotation, 'url') and 'aprende.org' in annotation.url:
                            url_recurso = annotation.url
                            logger.info(f"✅ URL encontrada en anotaciones: {url_recurso}")
                            break
            except:
                pass
        
        url_video = ""
        url_pdf = ""
        tipo_contenido = "webpage"
        
        # Extraer contenido multimedia si hay URL
        if url_recurso:
            try:
                logger.info("🎬 Extrayendo contenido multimedia...")
                contenido = asyncio.run(extraer_contenido_multimedia(url_recurso))
                tipo_contenido = contenido["tipo"]
                
                if tipo_contenido == "video":
                    url_video = contenido["url"]
                    logger.info(f"✅ Video extraído: {url_video}")
                elif tipo_contenido == "pdf":
                    url_pdf = contenido["url"]
                    logger.info(f"✅ PDF extraído: {url_pdf}")
                    
            except Exception as e:
                logger.error(f"❌ Error al extraer multimedia: {str(e)}")
                tipo_contenido = "webpage"
        
        # Detectar tipo de recurso
        tipo_recurso = detectar_tipo_recurso(url_recurso) if url_recurso else "general"
        
        # Construir resultado
        resultado = {
            "respuesta": texto_respuesta,
            "url_recurso": url_recurso,
            "url_video": url_video,
            "url_pdf": url_pdf,
            "tipo_contenido": tipo_contenido,
            "tipo_recurso": tipo_recurso
        }
        
        logger.info("✅ Respuesta completa generada")
        return resultado
        
    except Exception as e:
        logger.error(f"💥 Error en ask_about_vector_store: {str(e)}")
        raise