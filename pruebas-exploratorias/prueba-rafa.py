# ================================
# REQUERIMIENTOS:
# pip install openai hdbscan scikit-learn
# ================================

from openai import OpenAI
import numpy as np
import hdbscan
from sklearn.cluster import KMeans
from collections import defaultdict

client = OpenAI()

VECTOR_STORE_ID = "vs_693842808fa48191ad4813831ea4fe30"   # <<<<< CAMBIA AQUÍ


# ================================================================
# 1. Extraer TODOS los embeddings del Vector Store (paginado)
# ================================================================
def get_all_items_with_embeddings(vector_store_id):
    embeddings = []
    ids = []
    page_after = None

    while True:
        response = client.vector_stores.items.list(
            vector_store_id=vector_store_id,
            include=["embedding", "metadata"],
            limit=500,
            after=page_after
        )

        for item in response.data:
            if item.embedding is not None:
                ids.append(item.id)
                embeddings.append(item.embedding)

        if response.has_more:
            page_after = response.last_id
        else:
            break

    return ids, embeddings


print("🔍 Descargando embeddings del vector store...")
ids, embeddings = get_all_items_with_embeddings(VECTOR_STORE_ID)
print(f"✔ Descargados {len(ids)} embeddings.")

# Convertimos a numpy
X = np.array(embeddings)


# ================================================================
# 2. Aplicar CLUSTERING
# ================================================================

# --- Opción A: HDBSCAN (automático, recomendado)
print("🔎 Aplicando clustering con HDBSCAN...")
clusterer = hdbscan.HDBSCAN(min_cluster_size=10)
labels = clusterer.fit_predict(X)

# --- Opción B (opcional): K-Means
# print("🔎 Aplicando clustering con KMeans...")
# kmeans = KMeans(n_clusters=5, random_state=42)
# labels = kmeans.fit_predict(X)

print("✔ Clustering completado.")


# ================================================================
# 3. Agrupar los documentos por cluster
# ================================================================
clusters = defaultdict(list)

for doc_id, label in zip(ids, labels):
    clusters[label].append(doc_id)


# ================================================================
# 4. Guardar los clusters como metadata en el Vector Store
# ================================================================
print("💾 Guardando clusters dentro del Vector Store...")

for item_id, cluster in zip(ids, labels):
    client.vector_stores.items.update(
        vector_store_id=VECTOR_STORE_ID,
        item_id=item_id,
        metadata={"cluster": int(cluster)}
    )

print("✔ Metadatos de cluster guardados correctamente.")


# ================================================================
# Resumen final
# ================================================================
print("\n===== RESUMEN =====")
print(f"Total vectores: {len(ids)}")
print(f"Clusters encontrados: {len(set(labels))}")

print("\nTamaño de cada cluster:")
for c, docs in clusters.items():
    print(f" - Cluster {c}: {len(docs)} items")

print("\n¡Proceso completado sin reducción dimensional!")