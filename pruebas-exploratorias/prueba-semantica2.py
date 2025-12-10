import pandas as pd
from openai import OpenAI
from typing import List, Dict, Any
import os
from pathlib import Path

# Obtener API key desde variable de entorno o usar placeholder
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
if not OPENAI_API_KEY:
    raise ValueError("❌ Error: OPENAI_API_KEY no configurada. Establece la variable de entorno OPENAI_API_KEY")

VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID", "vs_6933017a9aa08191a0c0a728c78429cc")

client = OpenAI(api_key=OPENAI_API_KEY)

def buscar_solo_semantica(query: str, max_items: int = 10) -> None:
    """
    Muestra solo los cursos que encuentra la búsqueda semántica
    sin comparar con ningún DataFrame
    """
    print(f"\n🔍 BÚSQUEDA SEMÁNTICA: '{query}'")
    print("="*70)
    
    try:
        # 1. Hacer la búsqueda
        resp = client.vector_stores.search(
            vector_store_id=VECTOR_STORE_ID,
            query=query
        )
        
        # 2. Convertir a dict
        resp_dict = resp.to_dict()
        print(f"✅ Respuesta convertida a dict.")
        print(f"   Keys en respuesta: {list(resp_dict.keys())}")
        
        # 3. Extraer items
        items = resp_dict.get('data', [])
        print(f"📊 Total de items encontrados: {len(items)}")
        print(f"🔍 Mostrando hasta {min(max_items, len(items))} items:\n")
        
        if not items:
            print("⚠️ No hay items en la respuesta")
            return
        
        # 4. Procesar y mostrar cada item
        for i, item in enumerate(items[:max_items]):
            if not isinstance(item, dict):
                print(f"Item {i}: ❌ No es un diccionario")
                continue
                
            score = item.get('score', 0)
            file_id = item.get('file_id', 'N/A')
            filename = item.get('filename', 'N/A')
            
            print(f"📦 ITEM {i+1}:")
            print(f"   📊 Score: {score:.4f}")
            print(f"   📁 Archivo: {filename} (ID: {file_id})")
            
            # Buscar metadata en el content
            contenido = item.get('content', [])
            print(f"   📝 Elementos en content: {len(contenido)}")
            
            metadata_encontrado = False
            for j, elemento in enumerate(contenido):
                if not isinstance(elemento, dict):
                    continue
                    
                metadatos = elemento.get('metadata')
                if metadatos and isinstance(metadatos, dict):
                    metadata_encontrado = True
                    course_id = str(metadatos.get('courseId', 'N/A'))
                    course_name = metadatos.get('courseName', 'N/A')
                    num_recursos = metadatos.get('num_recursos', 'N/A')
                    
                    print(f"\n   🎯 METADATA (content {j}):")
                    print(f"      🆔 Course ID: {course_id}")
                    print(f"      📚 Course Name: {course_name}")
                    print(f"      📊 Número de recursos: {num_recursos}")
                    
                    # Mostrar más campos del metadata si existen
                    otros_campos = {k: v for k, v in metadatos.items() 
                                  if k not in ['courseId', 'courseName', 'num_recursos']}
                    if otros_campos:
                        print(f"      📋 Otros campos: {otros_campos}")
                
                # Mostrar preview del texto si existe
                texto = elemento.get('text', '')
                if texto:
                    preview = str(texto)[:150] + "..." if len(str(texto)) > 150 else str(texto)
                    print(f"      📄 Text preview: {preview}")
                    
                # Mostrar type si existe
                tipo = elemento.get('type', '')
                if tipo:
                    print(f"      🏷️  Type: {tipo}")
                    
                # Mostrar id si existe
                elemento_id = elemento.get('id', '')
                if elemento_id:
                    print(f"      🔖 ID: {elemento_id}")
            
            if not metadata_encontrado:
                print(f"   ⚠️  No se encontró metadata en este item")
            
            print("\n" + "-"*70)
        
        # 5. Mostrar resumen
        print(f"\n📊 RESUMEN DE LA BÚSQUEDA:")
        print(f"   Consulta: '{query}'")
        print(f"   Items totales: {len(items)}")
        print(f"   Items mostrados: {min(max_items, len(items))}")
        
        # Extraer todos los courseIds únicos encontrados
        course_ids = []
        course_names = []
        
        for item in items:
            if isinstance(item, dict):
                for elemento in item.get('content', []):
                    if isinstance(elemento, dict):
                        metadatos = elemento.get('metadata')
                        if metadatos and isinstance(metadatos, dict):
                            course_id = str(metadatos.get('courseId', ''))
                            course_name = metadatos.get('courseName', '')
                            if course_id and course_id != 'N/A':
                                course_ids.append(course_id)
                                if course_name:
                                    course_names.append(course_name)
        
        if course_ids:
            print(f"\n🎓 CURSOS ENCONTRADOS ({len(set(course_ids))} únicos):")
            for idx, (cid, cname) in enumerate(zip(course_ids, course_names)):
                if idx < 10:  # Mostrar solo primeros 10
                    print(f"   {idx+1:2}. ID: {cid} | Nombre: {cname}")
            
            if len(course_ids) > 10:
                print(f"   ... y {len(course_ids) - 10} más")
        else:
            print(f"\n⚠️  No se encontraron courseIds en los metadatos")
        
    except Exception as e:
        print(f"❌ Error en la búsqueda: {e}")
        import traceback
        traceback.print_exc()

# Función para hacer múltiples búsquedas
def buscar_varios_terminos(terminos: List[str]):
    """Busca varios términos y muestra los resultados"""
    for termino in terminos:
        buscar_solo_semantica(termino)
        input("\n⏎ Presiona Enter para continuar con el siguiente término...")

if __name__ == "__main__":
    print("🔍 BÚSQUEDA SEMÁNTICA PURA")
    print("="*60)
    
    # Opción: término único o varios
    print("\n1. Buscar un término específico")
    print("2. Probar varios términos comunes")
    
    opcion = input("Opción (1/2): ").strip()
    
    if opcion == "2":
        terminos = [
            "electricidad",
            "python",
            "fibra optica",
            "programación",
            "redes",
            "instalación",
            "técnico"
        ]
        buscar_varios_terminos(terminos)
    else:
        consulta = input("\n¿Qué quieres buscar?: ").strip()
        if not consulta:
            consulta = "electricidad"
            print(f"Usando término por defecto: '{consulta}'")
        
        buscar_solo_semantica(consulta, max_items=15)
    
    print("\n✅ Búsqueda completada!")