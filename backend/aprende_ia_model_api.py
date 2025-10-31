from dotenv import load_dotenv
from openai import OpenAI
import os
import re
import asyncio
from requests_html import AsyncHTMLSession
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


# ---------------------------------------------------------------------------
# 🔹 FUNCIÓN: Extraer contenido multimedia con requests-html
# ---------------------------------------------------------------------------
async def extraer_contenido_multimedia(resource_url: str) -> dict:
    """
    Intenta extraer contenido multimedia de la página de Aprende.org usando requests-html.
    Compatible con Render Free Tier.
    Prioridad: Video > PDF > Página completa
    
    Retorna un diccionario con:
    {
        "tipo": "video" | "pdf" | "webpage",
        "url": "URL del contenido encontrado"
    }
    """
    session = AsyncHTMLSession()
    logger.info(f"🔍 Accediendo a: {resource_url}")
    
    try:
        # Hacer la petición HTTP
        logger.info("📡 Realizando petición HTTP...")
        response = await session.get(resource_url, timeout=20)
        logger.info(f"✅ Status code: {response.status_code}")
        
        if response.status_code != 200:
            logger.warning(f"⚠️ Status code no exitoso: {response.status_code}")
            await session.close()
            return {"tipo": "webpage", "url": resource_url}
        
        # Renderizar JavaScript para contenido dinámico
        logger.info("🎬 Renderizando JavaScript...")
        try:
            await response.html.arender(timeout=20, sleep=3)
            logger.info("✅ JavaScript renderizado exitosamente")
        except Exception as render_error:
            logger.warning(f"⚠️ No se pudo renderizar JavaScript: {str(render_error)}")
            # Continuar con el HTML sin renderizar
        
        # Obtener el HTML completo
        html = response.html.html
        logger.info(f"📄 HTML obtenido. Longitud: {len(html)} caracteres")
        
        # ============ PASO 1: BUSCAR VIDEOS ============
        logger.info("🎥 Buscando videos en el HTML...")
        
        video_patterns = {
            'mp4_directo': r'https://[^\s\'"<>]+\.mp4(?:\?[^\s\'"<>]*)?',
            'm3u8_streaming': r'https://[^\s\'"<>]+\.m3u8(?:\?[^\s\'"<>]*)?',
            'vimeo_embed': r'https://player\.vimeo\.com/video/\d+',
            'vimeo_api': r'https://vimeo\.com/api/[^\s\'"<>]+',
            'youtube_embed': r'https://www\.youtube\.com/embed/[\w-]+',
            'youtube_watch': r'https://www\.youtube\.com/watch\?v=[\w-]+',
            'jwplayer': r'https://[^\s\'"<>]+\.mpd',
        }
        
        for nombre_patron, patron in video_patterns.items():
            match = re.search(patron, html, re.IGNORECASE)
            if match:
                url_video = match.group(0)
                logger.info(f"✅ Video encontrado con patrón '{nombre_patron}': {url_video}")
                await session.close()
                return {"tipo": "video", "url": url_video}
        
        logger.info("❌ No se encontraron videos")
        
        # ============ PASO 2: BUSCAR PDFs ============
        logger.info("📄 Buscando PDFs...")
        
        pdf_patterns = [
            r'https://[^\s\'"<>]+\.pdf(?:\?[^\s\'"<>]*)?',
            r'https://[^\s\'"<>]+/api/[^\s\'"<>]*\.pdf',
        ]
        
        for patron in pdf_patterns:
            match = re.search(patron, html, re.IGNORECASE)
            if match:
                url_pdf = match.group(0)
                logger.info(f"✅ PDF encontrado: {url_pdf}")
                await session.close()
                return {"tipo": "pdf", "url": url_pdf}
        
        logger.info("❌ No se encontraron PDFs")
        
        # ============ PASO 3: BUSCAR IFRAMES CON SELECTORES CSS ============
        logger.info("🖼️ Buscando iframes embebidos...")
        
        try:
            iframes = response.html.find('iframe')
            logger.info(f"📊 Encontrados {len(iframes)} iframes")
            
            for idx, iframe in enumerate(iframes):
                iframe_src = iframe.attrs.get('src', '')
                if iframe_src:
                    logger.info(f"   Iframe {idx+1}: {iframe_src[:100]}...")
                    
                    # Filtrar iframes que probablemente contengan videos
                    video_keywords = ['vimeo', 'youtube', 'player', 'video', 'wistia', 'embed']
                    if any(keyword in iframe_src.lower() for keyword in video_keywords):
                        logger.info(f"✅ Iframe de video encontrado: {iframe_src}")
                        await session.close()
                        return {"tipo": "video", "url": iframe_src}
        except Exception as iframe_error:
            logger.warning(f"⚠️ Error al buscar iframes: {str(iframe_error)}")
        
        logger.info("❌ No se encontraron iframes de video")
        
        # ============ PASO 4: FALLBACK - PÁGINA COMPLETA ============
        logger.info("📋 No se encontró contenido multimedia, usando página completa")
        await session.close()
        return {"tipo": "webpage", "url": resource_url}
        
    except asyncio.TimeoutError:
        logger.error("⏱️ Timeout al cargar la página")
        await session.close()
        return {"tipo": "webpage", "url": resource_url}
        
    except Exception as e:
        logger.error(f"💥 Error al extraer contenido: {str(e)}")
        try:
            await session.close()
        except:
            pass
        return {"tipo": "webpage", "url": resource_url}


# ---------------------------------------------------------------------------
# 🔹 FUNCIÓN: Detectar tipo de recurso basado en URL
# ---------------------------------------------------------------------------
def detectar_tipo_recurso(url: str) -> str:
    """
    Detecta el tipo de recurso educativo basándose en la URL.
    Returns: 'curso', 'diplomado', 'ruta', 'especialidad', 'general'
    """
    url_lower = url.lower()
    
    if '/cursos/' in url_lower or '/curso/' in url_lower:
        return 'curso'
    elif '/diplomado/' in url_lower or '/diplomados/' in url_lower:
        return 'diplomado'
    elif '/ruta/' in url_lower or '/rutas/' in url_lower:
        return 'ruta'
    elif '/especialidad/' in url_lower or '/especialidades/' in url_lower:
        return 'especialidad'
    else:
        return 'general'


# ---------------------------------------------------------------------------
# 🔹 FUNCIÓN PRINCIPAL: Consultar Vector Store
# ---------------------------------------------------------------------------
def ask_about_vector_store(question: str) -> dict:
    """
    Función principal para consultar el vector store de Aprende.org
    y obtener contenido multimedia (video/PDF) si está disponible.
    
    Retorna un diccionario con:
    {
        "respuesta": "Texto de respuesta del AI",
        "url_recurso": "URL de la página del recurso",
        "url_video": "URL del video (si existe)",
        "url_pdf": "URL del PDF (si existe)",
        "tipo_contenido": "video" | "pdf" | "webpage",
        "tipo_recurso": "curso" | "diplomado" | "ruta" | "especialidad"
    }
    """
    logger.info(f"🤖 Pregunta recibida: {question}")
    
    try:
        # ============ PASO 1: CONSULTAR VECTOR STORE ============
        logger.info("📚 Consultando vector store de OpenAI...")
        
        response = client.responses.create(
            model="gpt-4o-2024-11-20",
            input=[
                {
                    "role": "system",
                    "content": (
                        "Eres Claria, un asistente experto en capacitación profesional "
                        "de la Fundación Carlos Slim. Tu especialidad es ayudar a las personas "
                        "a encontrar cursos, diplomados y recursos educativos gratuitos en "
                        "Aprende.org. Siempre proporciona información útil y motivadora, "
                        "y cuando menciones un recurso, incluye su URL completa."
                    )
                },
                {
                    "role": "user",
                    "content": question
                }
            ],
            tools=[{
                "type": "file_search",
                "vector_store_ids": [vector_store_id],
                "max_num_results": 1
            }]
        )
        
        # Extraer texto de respuesta
        texto_respuesta = response.output_text.strip()
        logger.info(f"💬 Respuesta generada ({len(texto_respuesta)} caracteres)")
        
        # ============ PASO 2: EXTRAER URL DEL RECURSO ============
        logger.info("🔗 Extrayendo URL del recurso...")
        
        # Buscar URLs en el texto de respuesta
        patron_url = r'https?://[^\s\)\]\}\>\,\;\"\']+'
        coincidencias = re.findall(patron_url, texto_respuesta)
        
        # Filtrar URLs de Aprende.org
        urls_aprende = [
            url for url in coincidencias 
            if 'aprende.org' in url.lower()
        ]
        
        url_recurso = urls_aprende[0] if urls_aprende else ""
        
        if url_recurso:
            logger.info(f"✅ URL del recurso encontrada: {url_recurso}")
        else:
            logger.warning("⚠️ No se encontró URL de Aprende.org en la respuesta")
        
        # ============ PASO 3: EXTRAER CONTENIDO MULTIMEDIA ============
        url_video = ""
        url_pdf = ""
        tipo_contenido = "webpage"
        
        if url_recurso:
            try:
                logger.info("🎬 Intentando extraer contenido multimedia...")
                contenido = asyncio.run(extraer_contenido_multimedia(url_recurso))
                
                tipo_contenido = contenido["tipo"]
                
                if tipo_contenido == "video":
                    url_video = contenido["url"]
                    logger.info(f"✅ Video extraído: {url_video}")
                elif tipo_contenido == "pdf":
                    url_pdf = contenido["url"]
                    logger.info(f"✅ PDF extraído: {url_pdf}")
                else:
                    logger.info("📄 Se usará la página completa del recurso")
                    
            except Exception as e:
                logger.error(f"❌ Error al extraer contenido multimedia: {str(e)}")
                tipo_contenido = "webpage"
        
        # ============ PASO 4: DETECTAR TIPO DE RECURSO ============
        tipo_recurso = detectar_tipo_recurso(url_recurso) if url_recurso else "general"
        logger.info(f"🏷️ Tipo de recurso detectado: {tipo_recurso}")
        
        # ============ PASO 5: CONSTRUIR RESPUESTA FINAL ============
        resultado = {
            "respuesta": texto_respuesta,
            "url_recurso": url_recurso,
            "url_video": url_video,
            "url_pdf": url_pdf,
            "tipo_contenido": tipo_contenido,
            "tipo_recurso": tipo_recurso
        }
        
        logger.info("✅ Respuesta completa generada exitosamente")
        return resultado
        
    except Exception as e:
        logger.error(f"💥 Error en ask_about_vector_store: {str(e)}")
        raise


# ---------------------------------------------------------------------------
# 🔹 FUNCIÓN DE PRUEBA (Opcional)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Prueba rápida
    test_question = "Cursos de Python para principiantes"
    print("\n" + "="*60)
    print(f"🧪 PRUEBA: {test_question}")
    print("="*60 + "\n")
    
    resultado = ask_about_vector_store(test_question)
    
    print("\n" + "="*60)
    print("📊 RESULTADO:")
    print("="*60)
    print(f"✅ Respuesta: {resultado['respuesta'][:200]}...")
    print(f"🔗 URL Recurso: {resultado['url_recurso']}")
    print(f"🎥 URL Video: {resultado['url_video']}")
    print(f"📄 URL PDF: {resultado['url_pdf']}")
    print(f"📦 Tipo Contenido: {resultado['tipo_contenido']}")
    print(f"🏷️ Tipo Recurso: {resultado['tipo_recurso']}")
    print("="*60 + "\n")