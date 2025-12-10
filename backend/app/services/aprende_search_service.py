import logging
from typing import Any, Dict, List

from app.services.openai_vector_search_service import search_courses_in_vector_store

logger = logging.getLogger(__name__)


def is_aprende_intent(user_message: str, action: str = "") -> bool:
    """
    Heurística simple para activar el modo aprende.
    Ajusta según tu Router/Orchestrator.
    """
    t = (user_message or "").lower()
    a = (action or "").lower()
    return a == "aprende" or "aprende" in t or "cursos" in t


def run_aprende_flow(
    user_message: str,
    k: int = 5,
    fetch_top_n: int = 1,
) -> Dict[str, Any]:
    """
    Flujo de búsqueda de cursos (clusters).
    """
    logger.info(f"🚀 run_aprende_flow inicio | query='{user_message}' | k={k} | top={fetch_top_n}")

    if not user_message:
        logger.warning("User message vacío")
        return {"query": user_message, "candidates": [], "top": []}

    candidates: List[Dict[str, Any]] = search_courses_in_vector_store(user_message, k=k) or []
    
    logger.info(f"📊 Resultados de búsqueda: {len(candidates)} candidatos")
    
    # Depurar estructura de candidatos
    if candidates:
        logger.info("🔍 Detalle de candidatos:")
        for i, cand in enumerate(candidates[:5]):  # Mostrar primeros 5
            logger.info(f"  {i+1}. ID: {cand.get('id', 'N/A')}")
            logger.info(f"     Score: {cand.get('score', 'N/A')}")
            logger.info(f"     CourseName: {cand.get('courseName', 'N/A')}")
            logger.info(f"     CourseId: {cand.get('courseId', 'N/A')}")
            logger.info(f"     Metadata: {cand.get('metadata', {})}")
    
    top = candidates[:max(fetch_top_n, 0)] if candidates else []
    
    logger.info(f"✅ run_aprende_flow fin | candidatos={len(candidates)}, top={len(top)}")

    return {
        "query": user_message,
        "candidates": candidates,
        "top": top,
    }
