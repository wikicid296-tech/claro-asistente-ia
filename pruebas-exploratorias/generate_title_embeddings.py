import json
import os
import numpy as np
from typing import List, Dict
from openai import OpenAI

# =====================================================
# CONFIG
# =====================================================

INPUT_JSON_PATH = "cursos-con-ids.json"             # <-- pon aquí tu archivo real
OUTPUT_EMB_PATH = "title_embeddings.npz"     # <-- archivo final que copiarás a tu API
EMBEDDING_MODEL = "text-embedding-3-large"   # excelente calidad/costo

BATCH_SIZE = 100  # OpenAI embeddings permite listas grandes; 100 es seguro


# =====================================================
# LOAD JSON
# =====================================================

def load_courses(path: str) -> List[Dict]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"El archivo '{path}' no existe.")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Validación mínima
    if not isinstance(data, list):
        raise ValueError("El archivo JSON debe ser una lista de objetos.")

    for obj in data:
        if "courseId" not in obj or "courseName" not in obj:
            raise ValueError("Cada objeto debe contener 'courseId' y 'courseName'.")

    return data


# =====================================================
# GENERATE EMBEDDINGS
# =====================================================

def embed_texts(texts: List[str], client: OpenAI) -> np.ndarray:
    """
    Genera embeddings para una lista de textos usando batching.
    Devuelve una matriz NxD.
    """
    all_embeddings = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        print(f"→ Procesando batch {i} – {i + len(batch)}...")

        resp = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch
        )

        batch_embeddings = [item.embedding for item in resp.data]
        all_embeddings.extend(batch_embeddings)

    return np.array(all_embeddings, dtype=np.float32)


# =====================================================
# MAIN EXECUTION
# =====================================================

def main():
    print("=======================================")
    print("   GENERADOR DE EMBEDDINGS DE TÍTULOS  ")
    print("=======================================")

    api_key = ''
    if not api_key:
        raise EnvironmentError("Falta la variable OPENAI_API_KEY.")

    client = OpenAI(api_key=api_key)

    # 1. Cargar cursos
    print(f"\n📄 Leyendo archivo: {INPUT_JSON_PATH}")
    courses = load_courses(INPUT_JSON_PATH)
    print(f"✔ Cursos cargados: {len(courses)}")

    # Extraer listas alineadas
    course_ids = [c["courseId"] for c in courses]
    course_names = [c["courseName"] for c in courses]

    print("📄 Ejemplo: ")
    print("   ID:", course_ids[0])
    print("   Nombre:", course_names[0])

    # 2. Generar embeddings
    print("\n🧠 Generando embeddings para títulos...")
    embeddings = embed_texts(course_names, client)

    print("\n✔ Embeddings generados.")
    print("  → shape:", embeddings.shape)

    # 3. Guardar archivo NPZ
    print(f"\n💾 Guardando en: {OUTPUT_EMB_PATH}")
    np.savez(
        OUTPUT_EMB_PATH,
        course_ids=np.array(course_ids, dtype=object),
        course_names=np.array(course_names, dtype=object),
        title_embeddings=embeddings,
    )

    print("\n🎉 PROCESO COMPLETADO EXITOSAMENTE 🎉")
    print(f"Archivo generado: {OUTPUT_EMB_PATH}")


if __name__ == "__main__":
    main()
