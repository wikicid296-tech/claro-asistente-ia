# buscador.py
from openai import OpenAI
import re
import os
from dictcursos import id_curso_cursos as ID_CURSO_CURSOS

# Configuración
OPENAI_API_KEY = ''  # Cambia esto
VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID", "")  # Cambia esto si es necesario
print(f"🔧 Usando VECTOR_STORE_ID: {VECTOR_STORE_ID}")
# Inicializar cliente
client = OpenAI(api_key=OPENAI_API_KEY)

def buscar_cursos(query: str, top_k: int = 5):
    """
    Búsqueda ultra simple que devuelve lista de diccionarios con:
    - courseId
    - courseName (del diccionario)
    - score
    """
    
    print(f"🔍 Buscando: '{query}'")
    
    try:
        # 1. Hacer la búsqueda en OpenAI
        respuesta = client.vector_stores.search(
            vector_store_id=VECTOR_STORE_ID,
            query=query
        )
        
        resultados = []
        ids_vistos = set()  # Para evitar duplicados
        
        # 2. Procesar cada resultado
        for item in respuesta.data:
            try:
                # Obtener score
                score = item.score
                
                # Buscar courseId en el contenido
                course_id = None
                
                # Revisar todo el contenido del item
                for contenido in item.content:
                    if hasattr(contenido, 'text') and contenido.text:
                        # Buscar ID con regex
                        texto = contenido.text
                        
                        # Patrón para "courseId": número
                        match = re.search(r'"courseId":\s*(\d+)', texto)
                        if match:
                            course_id = match.group(1)
                            break
                        
                        # Patrón alternativo: curso-ID-
                        match = re.search(r'curso-(\d+)-', texto)
                        if match:
                            course_id = match.group(1)
                            break
                
                # Si no encontramos ID, saltar este resultado
                if not course_id:
                    continue
                
                # Evitar duplicados
                if course_id in ids_vistos:
                    continue
                ids_vistos.add(course_id)
                
                # Obtener nombre del diccionario
                course_name = ID_CURSO_CURSOS.get(course_id, "Curso no encontrado en diccionario")
                
                # Agregar resultado
                resultados.append({
                    "courseId": course_id,
                    "courseName": course_name,
                    "score": score
                })
                
                # Parar si ya tenemos suficientes
                if len(resultados) >= top_k:
                    break
                    
            except Exception as e:
                print(f"⚠️ Error en item: {e}")
                continue
        
        # 3. Ordenar por score (de mayor a menor)
        resultados.sort(key=lambda x: x["score"], reverse=True)
        
        print(f"✅ Encontrados: {len(resultados)} cursos")
        return resultados
        
    except Exception as e:
        print(f"❌ Error en búsqueda: {e}")
        return []

def mostrar_resultados(resultados):
    """Muestra los resultados en tabla simple"""
    if not resultados:
        print("\n😞 No se encontraron cursos.")
        return
    
    print("\n" + "="*80)
    print("📋 RESULTADOS")
    print("="*80)
    
    for i, r in enumerate(resultados, 1):
        print(f"{i:2d}. ID: {r['courseId']:4} | {r['courseName']:40} | Score: {r['score']:.4f}")
    
    print("="*80)

# Modo interactivo
if __name__ == "__main__":
    print("🔧 BÚSQUEDA SEMÁNTICA DE CURSOS")
    print("="*40)
    
    # Pedir consulta
    query = input("\n¿Qué quieres aprender?: ").strip()
    
    if not query:
        print("❌ Debes escribir algo para buscar")
        exit()
    
    # Buscar
    resultados = buscar_cursos(query, top_k=5)
    
    # Mostrar
    mostrar_resultados(resultados)
    
    print("\n✅ ¡Listo!")