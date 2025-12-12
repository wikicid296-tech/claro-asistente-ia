import logging
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from difflib import SequenceMatcher

from app.config import settings

logger = logging.getLogger(__name__)

# ==========================================================
# CONFIG
# ==========================================================

def get_openai_api_key() -> Optional[str]:
    return getattr(settings, "OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY")

def get_embedding_model() -> str:
    return (
        getattr(settings, "OPENAI_EMBEDDING_MODEL", None)
        or os.getenv("OPENAI_EMBEDDING_MODEL")
        or "text-embedding-3-large"
    )

def get_cluster_pack_path() -> str:
    env = getattr(settings, "COURSE_CLUSTER_PACK_PATH", None) or os.getenv("COURSE_CLUSTER_PACK_PATH")
    if env:
        return env
    here = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(here, "..", "data", "courses_cluster_pack.npz"))

def build_openai_client():
    api_key = get_openai_api_key()
    if not api_key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    except Exception as e:
        logger.error("No se pudo inicializar OpenAI client: %s", e, exc_info=True)
        return None

@lru_cache(maxsize=1)
def get_openai_client():
    return build_openai_client()

# ==========================================================
# LOAD PACK
# ==========================================================

@lru_cache(maxsize=1)
def load_cluster_pack() -> Dict[str, Any]:
    path = get_cluster_pack_path()
    if not os.path.exists(path):
        logger.warning("Cluster pack no encontrado en %s", path)
        return {}

    try:
        data = np.load(path, allow_pickle=True)
        return {k: data[k] for k in data.files}
    except Exception as e:
        logger.error("Error leyendo cluster pack: %s", e, exc_info=True)
        return {}

def _safe_get(pack: Dict[str, Any], *keys):
    for k in keys:
        if k in pack:
            return pack[k]
    return None

# ==========================================================
# EMBEDDINGS
# ==========================================================

def embed_query(text: str) -> Optional[np.ndarray]:
    client = get_openai_client()
    if not client:
        return None

    try:
        model = get_embedding_model()
        resp = client.embeddings.create(
            model=model,
            input=text
        )
        return np.array(resp.data[0].embedding, dtype=np.float32)
    except Exception as e:
        logger.error("Error generando embedding del query: %s", e, exc_info=True)
        return None

# ==========================================================
# SIMILARIDAD COSENO
# ==========================================================

def _cosine_sim_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a_norm = a / (np.linalg.norm(a) + 1e-10)
    b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-10)
    return np.dot(b_norm, a_norm)


# ==========================================================
# NUEVAS FUNCIONES PARA RE-RANKING SEMÁNTICO DE TÍTULOS
# ==========================================================

def _cosine_single(a: np.ndarray, b: np.ndarray) -> float:
    """Coseno entre dos vectores 1D."""
    return float(np.dot(a, b) / ((np.linalg.norm(a) + 1e-10) * (np.linalg.norm(b) + 1e-10)))


@lru_cache(maxsize=1)
def load_title_embeddings():
    """
    Carga embeddings de títulos generados externamente en title_embeddings.npz.
    Debe ubicarse en la MISMA carpeta que courses_cluster_pack.npz.
    """
    folder = os.path.dirname(get_cluster_pack_path())
    path = os.path.join(folder, "title_embeddings.npz")

    if not os.path.exists(path):
        print(f"⚠️ [title_embeddings] No existe archivo en: {path}")
        return None

    print(f"📚 Cargando title_embeddings desde: {path}")
    data = np.load(path, allow_pickle=True)

    return {
        "course_ids": data["course_ids"],
        "course_names": data["course_names"],
        "title_embeddings": data["title_embeddings"].astype(np.float32)
    }


def get_title_embedding_for_id(cid: str, title_pack):
    """Regresa el embedding del título cuyo ID coincide con cid."""
    ids = title_pack["course_ids"]
    idx = np.where(ids == cid)[0]

    if len(idx) == 0:
        return None

    return title_pack["title_embeddings"][idx[0]]

# ==========================================================
# RERANKING LÉXICO (TOKEN + SEQUENCEMATCHER)
# ==========================================================

LEXICAL_STOPWORDS = {
    "curso", "cursos", "taller", "talleres",
    "tecnico", "técnico", "tecnicos", "técnicos",
    "aprende", "aprender", "conoce", "conocer",
    "basico", "básico", "avanzado", "profesional",
    "en", "de", "para", "con", "por", "y", "o", "a",
    "la", "el", "los", "las"
}

def _normalize(text: str) -> str:
    return text.lower().strip() if text else ""

def _tokenize(text: str) -> List[str]:
    import re
    text = _normalize(text)
    tokens = re.findall(r"\w+", text, flags=re.UNICODE)
    return [t for t in tokens if len(t) > 2 and t not in LEXICAL_STOPWORDS]

def _lexical_similarity(query: str, title: str) -> float:
    """
    Similaridad léxica robusta usando n-grams + Jaccard aproximado.
    Esto capta similitud real incluso cuando no hay coincidencias literales.
    """
    if not query or not title:
        return 0.0

    def ngrams(text, n=3):
        text = _normalize(text)
        text = text.replace(" ", "")
        return {text[i:i+n] for i in range(len(text) - n + 1)}

    q_grams = ngrams(query, 3)
    t_grams = ngrams(title, 3)

    if not q_grams or not t_grams:
        return 0.0

    inter = len(q_grams & t_grams)
    union = len(q_grams | t_grams)

    return inter / union if union else 0.0


def apply_lexical_rerank(query: str, results: List[dict]) -> List[dict]:
    """
    Aplica re-ranking léxico SOLO si:
      - hay ≥2 resultados
      - top_score ∈ [0.35, 0.40]
      - delta < 0.02
    """
    print("\n============================")
    print("🔎 [DEBUG] Evaluando re-ranking léxico…")
    print("============================")

    if len(results) < 2:
        print("→ NO: menos de 2 resultados.")
        return results

    top = float(results[0]["score"])
    second = float(results[1]["score"])
    delta = top - second

    print(f"→ Top score:    {top:.4f}")
    print(f"→ Second score: {second:.4f}")
    print(f"→ Delta:        {delta:.4f}")
    print("→ Rango válido:", 0.35, "<= top <=", 0.40)

    if not (0.35 <= top <= 0.40):
        print("→ NO: Top fuera de rango.")
        return results

    if delta > 0.02:
        print("→ NO: delta demasiado grande.")
        return results

    print("→ SÍ: Activando re-ranking léxico.")

    # Calcular scores léxicos
    for r in results:
        cname = r.get("courseName") or ""
        lex = _lexical_similarity(query, cname)
        combined = r["score"] + 0.03 * lex  # pequeño boost
        r["_lex"] = lex
        r["_combined"] = combined

        print("\nCurso:", cname)
        print("  score original:", f"{r['score']:.4f}")
        print("  lex_score:     ", f"{lex:.4f}")
        print("  combined_score:", f"{combined:.4f}")

    print("\n→ Reordenando por combined_score…\n")

    results.sort(key=lambda x: x.get("_combined", x["score"]), reverse=True)

    print("🏁 ORDEN FINAL DESPUÉS DEL RERANKING:")
    for i, r in enumerate(results, 1):
        print(f" {i}. {r.get('courseName')} → combined={r.get('_combined'):.4f}")

    print("============================\n")
    return results

# ==========================================================
# SEARCH MAIN
# ==========================================================

def search_courses_in_clusters(query: str, k: int = 10) -> List[dict]:
    logger.info(f"🔍 Ejecutando búsqueda para query='{query}'")

    if not query:
        return []

    # Load cluster pack
    path = get_cluster_pack_path()
    if not os.path.exists(path):
        logger.error("Cluster pack no encontrado.")
        return []

    pack = load_cluster_pack()
    if not pack:
        logger.error("Cluster pack vacío.")
        return []

    embeddings = _safe_get(pack, "embeddings", "X", "vectors", "course_embeddings", "data")
    course_ids = _safe_get(pack, "course_ids", "ids", "indices")
    course_names = _safe_get(pack, "course_names", "names", "titles", "course_titles")
    labels = _safe_get(pack, "cluster_labels", "labels", "y")
    centroids = _safe_get(pack, "centroids", "cluster_centroids", "centers")

    # Normalize embeddings
    embeddings = np.asarray(embeddings, dtype=np.float32)
    course_ids = np.asarray(course_ids)
    course_names = np.asarray(course_names) if course_names is not None else None

    # Embedding del query
    q_vec = embed_query(query)
    if q_vec is None:
        return []

    # Selección por clusters
    if centroids is not None and labels is not None:
        c_sims = _cosine_sim_matrix(q_vec, np.asarray(centroids))
        top_clusters = np.argsort(c_sims)[::-1][:3]
        mask = np.isin(labels, top_clusters)
        idx_pool = np.where(mask)[0]
    else:
        idx_pool = np.arange(len(embeddings))

    pool_emb = embeddings[idx_pool]
    sims = _cosine_sim_matrix(q_vec, pool_emb)

    order = np.argsort(sims)[::-1][:k]

    # Build raw results
    results = []
    for rank_idx in order:
        real_idx = idx_pool[rank_idx]
        cid = str(course_ids[real_idx])
        cname = str(course_names[real_idx]) if course_names is not None else None

        results.append({
            "courseId": cid,
            "courseName": cname,
            "score": float(sims[rank_idx]),
            "metadata": {"courseId": cid, "courseName": cname},
        })

    # ==========================================
    # PRINT: ORDEN INICIAL
    # ==========================================
    print("\n############################################")
    print("➡️  ORDEN INICIAL ANTES DEL RE-RANKING")
    for i, r in enumerate(results, 1):
        print(f" {i}. {r['courseName']} → score={r['score']:.4f}")
    print("############################################\n")

    # ==========================================
    # APPLY RERANK
    # ==========================================
    results = apply_lexical_rerank(query, results)

    # ==========================================================
    # INICIO BLOQUE DE RE-RANKING SEMÁNTICO POR TÍTULO
    # ==========================================================

    print("\n==============================")
    print("🔍 Re-ranking semántico por título")
    print("==============================\n")

    title_pack = load_title_embeddings()

    if title_pack:
        print("➡️ Orden inicial según embeddings de contenido:")
        for i, r in enumerate(results, 1):
            print(f" {i}. {r['courseName']} → content={r['score']:.4f}")

        if len(results) >= 2:
            top = results[0]["score"]
            second = results[1]["score"]
            delta = top - second

            if 0.35 <= top <= 0.40 and delta < 0.02:
                print(f"✔ Re-ranking ACTIVADO (top={top:.4f}, delta={delta:.4f})\n")

                for r in results:
                    cid = str(r["courseId"])
                    t_emb = get_title_embedding_for_id(cid, title_pack)

                    if t_emb is None:
                        r["_title_sim"] = 0.0
                    else:
                        r["_title_sim"] = _cosine_single(q_vec, t_emb)

                    # combinación ponderada
                    r["_combined"] = 0.7 * r["score"] + 0.3 * r["_title_sim"]

                    print(f"→ {r['courseName']}")
                    print(f"    content_sim = {r['score']:.4f}")
                    print(f"    title_sim   = {r['_title_sim']:.4f}")
                    print(f"    combined    = {r['_combined']:.4f}\n")

                # Reordenar por combined
                results.sort(key=lambda x: x["_combined"], reverse=True)

                print("\n🏁 NUEVO ORDEN DESPUÉS DEL RE-RANKING:")
                for i, r in enumerate(results, 1):
                    print(f" {i}. {r['courseName']} → combined={r['_combined']:.4f}")

            else:
                print("❌ Re-ranking NO activado (fuera de umbral).")
        else:
            print("❌ No hay suficientes resultados para re-ranking.")

    else:
        print("⚠️ No se cargó title_embeddings; re-ranking desactivado.")

    print("\n==============================")
    print("🏁 Fin del re-ranking semántico")
    print("==============================\n")

    # ==========================================================
    # FIN BLOQUE DE RE-RANKING
    # ==========================================================

    # ==========================================
    # RESULTADOS FINALES
    # ==========================================
    print("\n############################################")
    print("🏁 RESULTADOS FINALES DESPUÉS DEL RE-RANKING")
    for i, r in enumerate(results, 1):
        print(f" {i}. {r['courseName']} → score={r['score']:.4f} | combined={r.get('_combined')}")
    print("############################################\n")

    return results
