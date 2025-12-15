import logging
from typing import List, Dict

from app.services.cluster_search_service import search_courses_in_clusters

logger = logging.getLogger(__name__)

# Umbral conservador para dominio válido
HIGH_THRESHOLD = 0.40   # dominio específico
LOW_THRESHOLD  = 0.28   # dominio procedimental válido


def evaluate_domain(noun: str) -> dict:
    """
    Evalúa pertenencia semántica al dominio Aprende usando clusters.
    Retorna decisión y tipo de dominio.
    """

    if not noun or noun == "NONE":
        return {"allowed": False, "reason": "no_noun"}

    results = search_courses_in_clusters(noun, k=3) or []
    if not results:
        return {"allowed": False, "reason": "no_results"}

    best_score = results[0]["score"]

    if best_score >= HIGH_THRESHOLD:
        return {
            "allowed": True,
            "mode": "specific",
            "score": best_score
        }

    if best_score >= LOW_THRESHOLD:
        return {
            "allowed": True,
            "mode": "procedural",
            "score": best_score
        }

    return {
        "allowed": False,
        "reason": "out_of_domain",
        "score": best_score
    }
