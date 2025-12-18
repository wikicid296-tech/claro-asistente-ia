from sentence_transformers import SentenceTransformer

print("🧠 Cargando modelo de embeddings (E5)...")

EMBEDDING_MODEL = SentenceTransformer(
    "intfloat/multilingual-e5-large"
)

print("✅ Modelo de embeddings cargado correctamente")
