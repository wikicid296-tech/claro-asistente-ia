import logging
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

# -----------------------------
# Config
# -----------------------------

def get_openai_api_key() -> Optional[str]:
    return (
        getattr(settings, "OPENAI_API_KEY", None)
        or os.getenv("OPENAI_API_KEY")
    )

def get_embedding_model() -> str:
    return (
        getattr(settings, "OPENAI_EMBEDDING_MODEL", None)
        or os.getenv("OPENAI_EMBEDDING_MODEL")
        or "text-embedding-3-large"
    )

def get_cluster_pack_path() -> str:
    # El usuario indicó que ya está en la carpeta data
    env = (
        getattr(settings, "COURSE_CLUSTER_PACK_PATH", None)
        or os.getenv("COURSE_CLUSTER_PACK_PATH")
    )
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

# -----------------------------
# Load pack
# -----------------------------

@lru_cache(maxsize=1)
def load_cluster_pack() -> Dict[str, Any]:
    path = get_cluster_pack_path()
    if not os.path.exists(path):
        logger.warning("Cluster pack no encontrado en %s", path)
        return {}

    try:
        data = np.load(path, allow_pickle=True)
        pack = {k: data[k] for k in data.files}
        return pack
    except Exception as e:
        logger.error("Error leyendo cluster pack: %s", e, exc_info=True)
        return {}

def _safe_get(pack: Dict[str, Any], *keys):
    for k in keys:
        if k in pack:
            return pack[k]
    return None

# -----------------------------
# Embeddings
# -----------------------------

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
        vec = np.array(resp.data[0].embedding, dtype=np.float32)
        return vec
    except Exception as e:
        logger.error("Error generando embedding del query: %s", e, exc_info=True)
        return None

# -----------------------------
# Similarity helpers
# -----------------------------

def _cosine_sim_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    # a: (D,), b: (N, D)
    a_norm = a / (np.linalg.norm(a) + 1e-10)
    b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-10)
    return np.dot(b_norm, a_norm)

# -----------------------------
# Main search
# -----------------------------

def search_courses_in_clusters(query: str, k: int = 10) -> List[dict]:
    """
    Búsqueda semántica local con clusters.
    """
    logger.info(f"🔍 search_courses_in_clusters llamado con query: '{query}', k: {k}")
    
    if not query:
        logger.warning("Query vacío")
        return []

    # Primero, verificar que el archivo existe
    path = get_cluster_pack_path()
    logger.info(f"📁 Buscando archivo en: {path}")
    logger.info(f"📁 Archivo existe: {os.path.exists(path)}")
    
    if not os.path.exists(path):
        logger.error(f"❌ Archivo no encontrado: {path}")
        return []

    pack = load_cluster_pack()
    if not pack:
        logger.error("❌ Cluster pack no cargado (diccionario vacío)")
        return []

    # Mostrar TODAS las claves tiene el pack
    logger.info(f"📦 TODAS las claves en pack: {list(pack.keys())}")
    
    # Mostrar información detallada de cada clave
    for key in pack.keys():
        value = pack[key]
        logger.info(f"🔑 Clave: '{key}'")
        logger.info(f"   Tipo: {type(value)}")
        if hasattr(value, 'shape'):
            logger.info(f"   Shape: {value.shape}")
        if hasattr(value, 'dtype'):
            logger.info(f"   Dtype: {value.dtype}")
        if hasattr(value, '__len__'):
            logger.info(f"   Length: {len(value)}")
            if len(value) > 0:
                if hasattr(value, 'shape') and len(value.shape) == 1:
                    if len(value) <= 5:
                        logger.info(f"   Valores: {value}")
                    else:
                        logger.info(f"   Primeros 5: {value[:5]}")
                elif isinstance(value, np.ndarray) and len(value.shape) == 2:
                    logger.info(f"   Shape: {value.shape}")
                    if value.shape[0] > 0:
                        logger.info(f"   Primera fila (muestra): {value[0][:5] if len(value[0]) > 5 else value[0]}...")

    # Intentar diferentes nombres posibles para las claves
    posibles_nombres_embeddings = [
        "embeddings", "X", "vectors", "embeddings_matrix", 
        "course_embeddings", "features", "data"
    ]
    
    posibles_nombres_ids = [
        "ids", "course_ids", "course_ids", "indices", 
        "course_numbers", "id", "course_id"
    ]
    
    # Buscar embeddings con diferentes nombres
    embeddings = None
    for nombre in posibles_nombres_embeddings:
        if nombre in pack:
            embeddings = pack[nombre]
            logger.info(f"✅ Encontrados embeddings en clave: '{nombre}'")
            break
    
    # Buscar course_ids con diferentes nombres
    course_ids = None
    for nombre in posibles_nombres_ids:
        if nombre in pack:
            course_ids = pack[nombre]
            logger.info(f"✅ Encontrados course_ids en clave: '{nombre}'")
            break
    
    # Si no encontramos con nombres estándar, intentar otros métodos
    if embeddings is None:
        # Buscar cualquier array 2D que podría ser embeddings
        for key, value in pack.items():
            if isinstance(value, np.ndarray) and len(value.shape) == 2:
                embeddings = value
                logger.info(f"⚠️ Usando como embeddings (por shape 2D): '{key}'")
                break
    
    if course_ids is None:
        # Buscar cualquier array 1D que podría ser IDs
        for key, value in pack.items():
            if isinstance(value, np.ndarray) and len(value.shape) == 1:
                course_ids = value
                logger.info(f"⚠️ Usando como course_ids (por shape 1D): '{key}'")
                break
    
    # Si aún no tenemos, mostrar error detallado
    if embeddings is None:
        logger.error("❌ NO SE ENCONTRARON EMBEDDINGS en el pack")
        logger.error("Claves disponibles:")
        for key in pack.keys():
            logger.error(f"  - '{key}': {type(pack[key])}")
            if hasattr(pack[key], 'shape'):
                logger.error(f"    Shape: {pack[key].shape}")
        return []
    
    if course_ids is None:
        logger.error("❌ NO SE ENCONTRARON COURSE_IDS en el pack")
        # Si tenemos embeddings pero no IDs, generar IDs artificiales
        logger.warning("⚠️ Generando IDs artificiales basados en índices")
        course_ids = np.arange(len(embeddings))
    
    # Ahora buscar otras claves opcionales
    course_names = _safe_get(pack, "course_names", "names", "titles", "course_titles")
    labels = _safe_get(pack, "cluster_labels", "labels", "y", "cluster_ids")
    centroids = _safe_get(pack, "centroids", "cluster_centroids", "centers")

    # Depuración detallada
    logger.info("=" * 60)
    logger.info("📊 RESUMEN DE DATOS ENCONTRADOS:")
    logger.info(f"   Embeddings: shape={embeddings.shape if hasattr(embeddings, 'shape') else 'N/A'}")
    logger.info(f"   Course IDs: shape={course_ids.shape if hasattr(course_ids, 'shape') else 'N/A'}")
    logger.info(f"   Course IDs sample: {course_ids[:5] if hasattr(course_ids, '__len__') and len(course_ids) > 0 else 'N/A'}")
    logger.info(f"   Course Names: {'Presente' if course_names is not None else 'Ausente'}")
    logger.info(f"   Labels: {'Presente' if labels is not None else 'Ausente'}")
    logger.info(f"   Centroids: {'Presente' if centroids is not None else 'Ausente'}")
    logger.info("=" * 60)
    
    # Normalizar tipos
    try:
        embeddings = np.asarray(embeddings, dtype=np.float32)
        logger.info(f"✅ Embeddings convertidos: shape={embeddings.shape}, dtype={embeddings.dtype}")
    except Exception as e:
        logger.error(f"❌ Error convirtiendo embeddings: {e}")
        return []
    
    try:
        course_ids = np.asarray(course_ids)
        logger.info(f"✅ Course IDs convertidos: shape={course_ids.shape}, dtype={course_ids.dtype}")
    except Exception as e:
        logger.error(f"❌ Error convirtiendo course_ids: {e}")
        return []



    if course_names is not None:
        try:
            course_names = np.asarray(course_names)
            logger.info(f"✅ Course Names convertidos: shape={course_names.shape}")
        except Exception as e:
            logger.warning(f"⚠️ Error convirtiendo course_names: {e}")
            course_names = None
    
    if labels is not None:
        try:
            labels = np.asarray(labels)
            logger.info(f"✅ Labels convertidos: shape={labels.shape}")
        except Exception as e:
            logger.warning(f"⚠️ Error convirtiendo labels: {e}")
            labels = None
    
    if centroids is not None:
        try:
            centroids = np.asarray(centroids, dtype=np.float32)
            logger.info(f"✅ Centroids convertidos: shape={centroids.shape}")
        except Exception as e:
            logger.warning(f"⚠️ Error convirtiendo centroids: {e}")
            centroids = None

    # Generar embedding del query
    logger.info(f"🧠 Generando embedding para query: '{query}'")
    q_vec = embed_query(query)
    if q_vec is None:
        logger.error("❌ No se pudo generar embedding del query")
        return []
    
    logger.info(f"✅ Query vector generado: shape={q_vec.shape}, norm={np.linalg.norm(q_vec)}")

    # 1) Selección de candidatos por cluster (si hay centroids y labels)
    idx_pool = None
    if centroids is not None and labels is not None:
        try:
            logger.info("🎯 Usando selección por clusters")
            c_sims = _cosine_sim_matrix(q_vec, centroids)  # (K,)
            logger.info(f"📊 Similitudes con centroides: shape={c_sims.shape}")
            logger.info(f"📊 Valores de similitud: {c_sims}")
            
            top_cluster_idx = np.argsort(c_sims)[::-1][:3]  # top 3 clusters
            logger.info(f"📊 Top 3 clusters: {top_cluster_idx}")
            
            mask = np.isin(labels, top_cluster_idx)
            idx_pool = np.where(mask)[0]
            logger.info(f"📊 Índices en pool: {len(idx_pool)} de {len(embeddings)} totales")
        except Exception as e:
            logger.warning(f"⚠️ Fallo selección por centroides, se usará full scan: {e}")
            idx_pool = None

    # 2) Calcular similitud final dentro del pool
    if idx_pool is None or len(idx_pool) == 0:
        logger.info("🎯 Usando búsqueda completa (full scan)")
        idx_pool = np.arange(len(embeddings))

    logger.info(f"📊 Pool final de búsqueda: {len(idx_pool)} elementos")

    pool_emb = embeddings[idx_pool]
    logger.info(f"📊 Embeddings en pool: shape={pool_emb.shape}")

    sims = _cosine_sim_matrix(q_vec, pool_emb)  # (pool,)
    logger.info(f"📊 Similitudes calculadas: shape={sims.shape}")
    logger.info(f"📊 Rango de scores: min={sims.min():.4f}, max={sims.max():.4f}, mean={sims.mean():.4f}")

    order = np.argsort(sims)[::-1][:k]
    logger.info(f"📊 Índices ordenados (top {k}): {order}")

    results = []
    for rank_idx in order:
        real_idx = idx_pool[rank_idx]
        cid = course_ids[real_idx]
        cname = None

        if course_names is not None and real_idx < len(course_names):
            cname = course_names[real_idx]

        # Convertir tipos robustos
        cid_str = str(cid)
        cname_str = str(cname) if cname is not None else None

        score = float(sims[rank_idx])

        meta = {}
        # Mantener tu shape de metadata
        # courseId numérico si se puede
        try:
            meta["courseId"] = int(cid_str) if cid_str.isdigit() else cid_str
        except Exception:
            meta["courseId"] = cid_str

        if cname_str:
            meta["courseName"] = cname_str

        processed = {
            "id": cid_str,
            "score": score,
            "metadata": meta,
            "courseName": cname_str,
            "courseId": meta["courseId"],
        }
        results.append(processed)
        
        # Log detallado para primeros resultados
        if len(results) <= 3:
            logger.info(f"   📝 Resultado {len(results)}:")
            logger.info(f"      ID: {cid_str}")
            logger.info(f"      Score: {score:.4f}")
            logger.info(f"      Nombre: {cname_str or 'N/A'}")
            logger.info(f"      Metadata: {meta}")

    logger.info(f"✅ search_courses_in_clusters finalizado: {len(results)} resultados encontrados")
    
    # Mostrar resumen de scores
    if results:
        scores = [r.get('score', 0) for r in results]
        logger.info(f"📊 Resumen scores: min={min(scores):.4f}, max={max(scores):.4f}, avg={sum(scores)/len(scores):.4f}")
    
    return results