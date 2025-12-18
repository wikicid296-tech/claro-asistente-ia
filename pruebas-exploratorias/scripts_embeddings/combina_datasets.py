import pandas as pd
from pymongo import MongoClient
from tqdm import tqdm

# =========================
# CONFIGURACIÓN GENERAL
# =========================

MONGO_URI = ''
DB_NAME = "telcel_rag"
COLLECTION_NAME = "embeddings"

EMBEDDING_DIM = 1024
BATCH_SIZE = 500

# =========================
# ARCHIVOS PKL
# =========================

PKL_FILES = [
    {
        "path": "../embeddings_telcel/telcel_embeddings_with_vectors.pkl",
        "dataset": "telcel_basico",
        "id_prefix": "basico"
    },
    {
        "path":  "../embeddings_telcel/telcel_embeddings_planes_with_vectors.pkl",
        "dataset": "tarifas",
        "id_prefix": "tarifas"
    }
]

# =========================
# CONEXIÓN A MONGO
# =========================

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
col = db[COLLECTION_NAME]

# =========================
# VACIAR COLECCIÓN (UNA SOLA VEZ)
# =========================

print("Vaciando colección completa...")
col.delete_many({})
print("Colección vacía.\n")

# =========================
# FUNCIÓN DE VALIDACIÓN
# =========================

def embedding_valido(e):
    return (
        isinstance(e, list)
        and len(e) == EMBEDDING_DIM
        and all(isinstance(x, (float, int)) for x in e)
    )

# =========================
# CARGA DE CADA PKL
# =========================

total_insertados = 0

for cfg in PKL_FILES:
    print(f"Cargando dataset: {cfg['dataset']}")
    df = pd.read_pickle(cfg["path"])
    print(f"Filas originales: {len(df)}")

    df = df[df["embedding"].apply(embedding_valido)].reset_index(drop=True)
    print(f"Filas válidas: {len(df)}")

    docs = []
    for row in tqdm(df.itertuples(), total=len(df)):
        docs.append({
            "_id": f"{cfg['id_prefix']}_{row.id}",
            "dataset": cfg["dataset"],
            "embedding": list(row.embedding),
            "titulo": getattr(row, "titulo", None),
            "texto": getattr(row, "texto_embedding", None),
            "categoria": getattr(row, "categoria", None),
            "subtipo": getattr(row, "subtipo", None),
            "url": getattr(row, "url", None),
            "idioma": getattr(row, "idioma", "es"),
            "fecha_extraccion": getattr(row, "fecha_extraccion", None),
        })

    for i in range(0, len(docs), BATCH_SIZE):
        col.insert_many(docs[i:i+BATCH_SIZE])

    print(f"Insertados {len(docs)} documentos de {cfg['dataset']}\n")
    total_insertados += len(docs)

# =========================
# RESUMEN FINAL
# =========================

print("Carga completa.")
print("Total documentos en colección:", col.count_documents({}))
print("Total insertados:", total_insertados)

print("\nConteo por dataset:")
print(list(col.aggregate([
    { "$group": { "_id": "$dataset", "count": { "$sum": 1 } } }
])))
