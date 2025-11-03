from dotenv import load_dotenv
from openai import OpenAI
import os
import re
import asyncio
from playwright.async_api import async_playwright
import logging

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
    Función principal para consultar el vector store de Aprende.org
    y SIEMPRE entregar un recurso educativo.
    """
    logger.info(f"🤖 Pregunta recibida: {question}")
    
    try:
        logger.info("📚 Consultando vector store de OpenAI...")
        
        response = client.responses.create(
            model="gpt-4o-2024-11-20",
            input=[
                {
                    "role": "system",
                    "content": (
                        "Eres Claria, asistente experta de la Fundación Carlos Slim especializada en Aprende.org.\n\n"
                        
                        "🎯 TU MISIÓN PRINCIPAL:\n"
                        "Para CADA consulta del usuario, debes SIEMPRE:\n"
                        "1. Buscar el curso, diplomado o recurso MÁS relevante en Aprende.org\n"
                        "2. Explicar brevemente el recurso (2-3 oraciones máximo)\n"
                        "3. INCLUIR LA URL COMPLETA del recurso (https://aprende.org/...)\n\n"
                        
                        "📋 REGLAS OBLIGATORIAS:\n"
                        "• NUNCA respondas sin ofrecer un recurso específico de Aprende.org\n"
                        "• SIEMPRE incluye la URL del curso/diplomado aunque el usuario no la pida explícitamente\n"
                        "• Si el usuario pregunta sobre conceptos o definiciones, ofrece el curso relacionado\n"
                        "• Si el usuario es principiante o nuevo, recomienda cursos para principiantes\n"
                        "• Si no encuentras un recurso exacto, ofrece el más cercano y explica por qué es relevante\n"
                        "• Si preguntan 'qué me sugieres' o 'ayúdame', recomienda un curso popular o introductorio\n\n"
                        
                        "✅ EJEMPLO DE RESPUESTA CORRECTA:\n"
                        "'Para aprender ciberseguridad desde cero, te recomiendo el curso "
                        "\"Fundamentos de Ciberseguridad\" que cubre conceptos básicos, tipos de amenazas "
                        "y buenas prácticas de protección. Es ideal para principiantes y totalmente gratuito.\n\n"
                        "Puedes acceder aquí: https://aprende.org/cursos/302'\n\n"
                        
                        "❌ NUNCA hagas esto:\n"
                        "• Responder sin mencionar un recurso específico\n"
                        "• Dar solo información teórica sin enlace a curso\n"
                        "• Decir 'no tengo información' (siempre busca algo relacionado)\n"
                        "• Pedir más detalles antes de ofrecer un recurso\n\n"
                        
                        "🔑 PALABRAS CLAVE DEL USUARIO:\n"
                        "• 'Qué es...' → Explica brevemente + ofrece curso introductorio\n"
                        "• 'Dame un recurso' → Ofrece el curso más relevante directamente\n"
                        "• 'Soy nuevo/principiante' → Ofrece curso para principiantes\n"
                        "• 'Ayúdame/sugiéreme' → Ofrece curso popular del tema más cercano\n"
                        "• 'Curso de...' → Busca curso específico del tema\n\n"
                        
                        "Sé amable, motivador y SIEMPRE entrega un recurso concreto."
                    )
                },
                {"role": "user", "content": question}
            ],
            tools=[{
                "type": "file_search",
                "vector_store_ids": [vector_store_id],
                "max_num_results": 3  # Buscar hasta 3 resultados para mayor precisión
            }]
        )
        
        texto_respuesta = response.output_text.strip()
        logger.info(f"💬 Respuesta generada ({len(texto_respuesta)} caracteres)")
        
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
                logger.error(f"❌ Error al extraer: {str(e)}")
                tipo_contenido = "webpage"
        
        tipo_recurso = detectar_tipo_recurso(url_recurso) if url_recurso else "general"
        
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
        logger.error(f"💥 Error: {str(e)}")
        raise