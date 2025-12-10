# recommend.py
# ================================
# pip install numpy pandas scikit-learn openai
# ================================

from __future__ import annotations

import numpy as np
from openai import OpenAI
from sklearn.preprocessing import normalize
from sklearn.metrics.pairwise import cosine_similarity


PACK_NPZ = "courses_cluster_pack.npz"
EMBED_MODEL = "text-embedding-3-large"
OPENAI_API_KEY = ''  # Cambia esto


client = OpenAI(api_key=OPENAI_API_KEY)


def load_pack(path: str):
    data = np.load(path, allow_pickle=True)
    ids = data["ids"]
    names = data["names"]
    X = data["X"]          # ya normalizado
    labels = data["labels"]
    centroids = data["centroids"]  # ya en espacio normalizado
    return ids, names, X, labels, centroids


def embed_query(text: str) -> np.ndarray:
    resp = client.embeddings.create(
        model=EMBED_MODEL,
        input=text,
        encoding_format="float"
    )
    v = np.array(resp.data[0].embedding, dtype=np.float32).reshape(1, -1)
    v = normalize(v)
    return v


def assign_cluster(v: np.ndarray, centroids: np.ndarray) -> int:
    # Para KMeans, asignar por centroides == criterio natural
    sims = cosine_similarity(v, centroids)  # (1, K)
    return int(np.argmax(sims))


def recommend_courses(text: str, top_k: int = 10):
    ids, names, X, labels, centroids = load_pack(PACK_NPZ)

    v = embed_query(text)
    c = assign_cluster(v, centroids)

    # Filtra por cluster
    mask = labels == c
    Xc = X[mask]
    idsc = ids[mask]
    namesc = names[mask]

    # Rank por similitud
    sims = cosine_similarity(v, Xc).flatten()
    order = np.argsort(-sims)[:top_k]

    results = []
    for i in order:
        results.append({
            "courseId": str(idsc[i]),
            "courseName": str(namesc[i]),
            "score": float(sims[i]),
            "cluster": c
        })

    return results


if __name__ == "__main__":
    query = input("Introduce tu consulta para recomendar cursos: ")
    recs = recommend_courses(query, top_k=5)
    for r in recs:
        print(r)
