import os
import sys
from dotenv import load_dotenv
from openai import OpenAI
import numpy as np
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE

# ==========================================================
# 🔐 Cargar y validar variables .env
# ==========================================================

load_dotenv()

def load_env(name):
    v = os.getenv(name)
    if not v:
        print(f"❌ Falta la variable {name}")
        sys.exit(1)
    return v

OPENAI_API_KEY = load_env("OPENAI_API_KEY")
VECTOR_STORE_ID = load_env("VECTOR_STORE_ID")

client = OpenAI(api_key=OPENAI_API_KEY)


# ==========================================================
# 📄 Descargar archivos del Vector Store
# ==========================================================

def fetch_files(vector_store_id):
    """
    Obtiene la lista de archivos vinculados al Vector Store.
    Nota: Se necesitan dos llamadas: una para la relación y otra para los detalles del archivo.
    """
    print(f"📄 Listando archivos del vector store {vector_store_id}...")
    
    # 1. Obtener la lista de referencias (VectorStoreFiles)
    # Nota: Los Vector Stores están bajo el namespace 'beta'
    cursor = client.vector_stores.files.list(vector_store_id=vector_store_id)

    files_data = []
    
    for vs_file in cursor:
        try:
            # 2. Obtener detalles del archivo real (para ver el nombre)
            file_details = client.files.retrieve(vs_file.id)
            
            # Guardamos un diccionario con lo que necesitamos
            file_info = {
                "id": file_details.id,          # ID real del archivo (file-...)
                "vs_id": vs_file.id,            # ID de la relación
                "filename": file_details.filename,
                "metadata": {}                  # La API de Files estándar no siempre trae metadata personalizada aquí
            }
            
            files_data.append(file_info)
            print(f"  ➤ {file_info['id']} | {file_info['filename']}")
            
        except Exception as e:
            print(f"  ⚠️ Error obteniendo detalles para {vs_file.id}: {e}")

    return files_data


def download_file_content(file_id):
    """Descarga el contenido crudo. Solo funciona bien para archivos de texto plano."""
    print(f"📥 Descargando contenido de {file_id}...")
    try:
        response = client.files.content(file_id)
        # Intentamos decodificar como texto. Si es PDF/Img, esto fallará.
        return response.read().decode("utf-8")
    except UnicodeDecodeError:
        print(f"  ❌ El archivo {file_id} parece binario (PDF/Imagen). Se omitirá el contenido.")
        return ""
    except Exception as e:
        print(f"  ❌ Error descargando {file_id}: {e}")
        return ""


# ==========================================================
# ✨ Generar embeddings y etiquetas
# ==========================================================

def chunk_text(text, max_tokens=500):
    """Chunk simple basado en espacios (aproximación)."""
    if not text:
        return
    words = text.split()
    if not words:
        return
        
    for i in range(0, len(words), max_tokens):
        yield " ".join(words[i:i + max_tokens])


def generate_embeddings_for_store(files_data):
    vectors = []
    labels = []
    texts = []

    print("\n🧠 Generando embeddings...")
    
    if not files_data:
        print("⚠️ No se encontraron archivos para procesar.")
        return np.array([]), np.array([]), []

    for f in files_data:
        raw_text = download_file_content(f['id'])
        
        if not raw_text:
            continue

        # Usamos el nombre del archivo como etiqueta si no hay categoría
        label = f['filename']

        # Iterar sobre chunks
        for chunk in chunk_text(raw_text, 300):
            try:
                emb = client.embeddings.create(
                    model="text-embedding-3-small", # 'small' es más barato y rápido para pruebas
                    input=chunk
                )
                vectors.append(emb.data[0].embedding)
                labels.append(label)
                texts.append(chunk)
            except Exception as e:
                print(f"Error generando embedding: {e}")

    print(f"✅ Total embeddings generados: {len(vectors)}\n")
    return np.array(vectors), np.array(labels), texts


# ==========================================================
# 🔻 Visualización
# ==========================================================

def visualize(vectors, labels):
    if len(vectors) < 2:
        print("⚠️ No hay suficientes vectores para visualizar (mínimo 2).")
        return

    print("🔻 Ejecutando TSNE para visualización...")
    
    # Ajuste dinámico de perplejidad para evitar errores con pocos datos
    n_samples = len(vectors)
    perplexity_val = min(30, n_samples - 1)
    
    tsne = TSNE(n_components=2, perplexity=perplexity_val, random_state=42, init='pca', learning_rate=200)
    points = tsne.fit_transform(vectors)

    print("📊 Mostrando gráfica...")

    unique_labels = sorted(set(labels))
    
    # Manejo de colores
    cmap = plt.get_cmap('tab20')
    colors = cmap(np.linspace(0, 1, len(unique_labels)))

    plt.figure(figsize=(12, 8))

    for label, color in zip(unique_labels, colors):
        m = labels == label
        plt.scatter(points[m, 0], points[m, 1],
                    s=60, color=color, label=label, alpha=0.7, edgecolors='k')

    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.title(f"Mapa Vectorial ({n_samples} chunks)")
    plt.tight_layout()
    plt.show()


# ==========================================================
# 🚀 MAIN
# ==========================================================

if __name__ == "__main__":
    files = fetch_files(VECTOR_STORE_ID)
    
    vectors, labels, texts = generate_embeddings_for_store(files)
    
    if len(vectors) > 0:
        visualize(vectors, labels)
    else:
        print("🛑 No se generaron vectores. Verifica que los archivos en el Vector Store sean de texto (.txt, .md, .py, .json).")