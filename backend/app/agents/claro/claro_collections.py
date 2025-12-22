# agents/claro/claro_collections.py
from typing import Optional, Dict


# =====================================================
# CONFIGURACIÓN DE COLECCIONES E ÍNDICES POR PAÍS
# =====================================================

CLARO_VECTOR_CONFIG: Dict[str, Dict[str, str]] = {
    "ar": {
        "collection": "embeddings_claro_argentina",
        "vector_index": "claro_argentina",
    },
    "co": {
        "collection": "embeddings_claro_colombia",
        "vector_index": "claro_colombia",
    },
    "br": {
        "collection": "embeddings_claro_brasil",
        "vector_index": "claro_brasil",
    },
    # 👉 futuros países:
    # "mx": {
    #     "collection": "embeddings_claro_mexico",
    #     "vector_index": "vector_index",
    # },
}


# =====================================================
# RESOLVERS (USADOS POR EL AGENTE)
# =====================================================

def resolve_claro_collection(country: str) -> Optional[str]:
    """
    Devuelve el nombre de la colección Mongo para el país indicado.
    """
    config = CLARO_VECTOR_CONFIG.get(country)
    return config.get("collection") if config else None


def resolve_claro_vector_index(country: str) -> Optional[str]:
    """
    Devuelve el nombre del índice vectorial a usar para el país indicado.
    """
    config = CLARO_VECTOR_CONFIG.get(country)
    return config.get("vector_index") if config else None


def resolve_claro_vector_config(country: str) -> Optional[Dict[str, str]]:
    """
    Devuelve la configuración completa (colección + índice).
    Útil si el agente quiere inicializar el RAG de una sola vez.
    """
    return CLARO_VECTOR_CONFIG.get(country)
