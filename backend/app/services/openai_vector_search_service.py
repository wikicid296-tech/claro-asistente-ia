# backend/app/services/openai_vector_search_service.py

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.services.cluster_search_service import search_courses_in_clusters

logger = logging.getLogger(__name__)


def search_courses_in_vector_store(query: str, k: int = 5, **_ignored) -> List[Dict[str, Any]]:
    """
    Adapter de compatibilidad.
    """
    logger.info(f"🔍 search_courses_in_vector_store llamado: query='{query}', k={k}")
    
    if not query or not query.strip():
        logger.warning("Query vacío o solo espacios")
        return []

    try:
        results = search_courses_in_clusters(query, k=k) or []
        logger.info(f"✅ search_courses_in_vector_store resultados: {len(results)} cursos")
        
        # Verificar estructura de resultados
        if results:
            logger.info("📋 Estructura del primer resultado:")
            logger.info(f"   Keys: {list(results[0].keys())}")
            logger.info(f"   Metadata keys: {list(results[0].get('metadata', {}).keys())}")
            logger.info(f"   Sample: ID={results[0].get('id')}, Name={results[0].get('courseName', 'N/A')}")
        
        return results
    except Exception as e:
        logger.error(f"❌ Cluster search error: {e}", exc_info=True)
        return []