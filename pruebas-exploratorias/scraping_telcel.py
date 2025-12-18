import json
import re
from playwright.sync_api import sync_playwright

def limpiar_texto(texto):
    """Limpia espacios dobles y saltos de línea para optimizar tokens."""
    if not texto: return "N/A"
    return re.sub(r'\s+', ' ', texto).strip()

def extraer_planes_telcel():
    data_para_bot = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # URL específica de la oferta comercial actual (puede cambiar, revisar sitemap)
        url_planes = "https://www.telcel.com/planes-renta"
        
        print(f"--- Indexando: {url_planes} ---")
        page.goto(url_planes, timeout=60000, wait_until="networkidle")

        # MANEJO DE REGIÓN (Crucial para precios correctos)
        # Si no seleccionas región, los precios pueden salir en $0 o vacíos.
        try:
            btn_region = page.locator("button:has-text('Confirmar'), button:has-text('Guardar')").first
            if btn_region.is_visible():
                btn_region.click()
                page.wait_for_timeout(2000)
        except:
            pass

        # ESTRATEGIA: Buscar contenedores de planes.
        # Telcel usa cards que suelen tener clases como 'c-card-plan', 'm-card', etc.
        # Usaremos selectores basados en contenido para mayor resiliencia.
        
        # Buscamos elementos que contengan el signo de pesos "$" y la palabra "GB"
        # Esto es heurística para encontrar cards de planes.
        print("--- Buscando patrones de tarifas en el DOM ---")
        
        # Nota: Este selector es amplio para capturar varios tipos de layout
        cards = page.locator(".o-card-plan, .c-card, div[class*='card']:has-text('$')")
        
        count = cards.count()
        print(f"Se encontraron {count} posibles planes.")

        for i in range(count):
            card = cards.nth(i)
            
            # Extraemos texto crudo
            raw_text = card.inner_text()
            
            # Si el bloque tiene muy poco texto, probablemente no es un plan
            if len(raw_text) < 20: continue

            # Intentamos parsear datos específicos con selectores internos relativos
            # El uso de try/except es vital porque no todas las cards son iguales
            try:
                nombre = card.locator("h3, h4, .title").first.inner_text()
            except:
                nombre = "Plan Sin Nombre Detectado"

            try:
                precio = card.locator(":text-matches('\\$')").first.inner_text()
            except:
                precio = "Consultar"

            # Limpieza
            nombre = limpiar_texto(nombre)
            precio = limpiar_texto(precio)
            descripcion = limpiar_texto(raw_text)

            # ESTRUCTURA PARA RAG / LLM
            # Creamos un bloque de texto denso semánticamente para los embeddings
            contexto_semantico = (
                f"El plan denominado '{nombre}' tiene un costo aproximado de {precio}. "
                f"Los detalles y beneficios completos incluyen: {descripcion}."
            )

            item = {
                "source_url": url_planes,
                "category": "Planes de Renta",
                "entity": nombre,
                "price_raw": precio,
                "full_text": descripcion,
                "llm_context": contexto_semantico # <--- ESTO ES LO QUE TU BOT LEERÁ
            }
            
            data_para_bot.append(item)

        browser.close()

    return data_para_bot

if __name__ == "__main__":
    datos = extraer_planes_telcel()
    
    # Guardamos en JSONL (formato ideal para datasets de entrenamiento/ingesta)
    with open("telcel_knowledge_base.jsonl", "w", encoding="utf-8") as f:
        for entry in datos:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            
    print(f"Proceso finalizado. {len(datos)} registros exportados para el bot.")