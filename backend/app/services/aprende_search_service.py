import logging
import re
from typing import Any, Dict, List

from app.services.cluster_search_service import search_courses_in_clusters
from app.services.noun_extraction_service import extract_main_noun
from app.services.semantic_guard_service import evaluate_domain

logger = logging.getLogger(__name__)


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

    # =====================================================
    # BYPASS: Curso solicitado explícitamente por ID
    # =====================================================
    def extract_course_id(text: str):
        t = (text or "").lower()
        patterns = [
            r'\bcurso\s*(?:no\.?|número|numero|#)?\s*(\d+)\b',
            r'\bno\.?\s*(\d+)\b',
            r'\b#(\d+)\b',
            r'\b(\d{1,4})\b'
        ]
        for p in patterns:
            m = re.search(p, t)
            if m:
                return m.group(1)
        return None

    course_id = extract_course_id(user_message)
    if course_id:
        logger.info(f"🎯 Bypass Aprende activado | Curso solicitado por ID explícito: {course_id}")
        try:
            from app.services.aprende_courses_api_service import get_course_by_id

            course = get_course_by_id(course_id)
            if course:
                logger.info(f"✅ Curso {course_id} encontrado, retornando directo")
                return {
                    "query": user_message,
                    "candidates": [course],
                    "top": [course],
                }
            else:
                logger.info(f"❌ Curso {course_id} no encontrado, continuando flujo semántico")
        except Exception:
            logger.exception("Error en bypass por ID, continuando flujo semántico")

    # =====================================================
    # EXTRACCIÓN DE SUSTANTIVO NÚCLEO (Groq)
    # =====================================================
    extraction = extract_main_noun(user_message)
    main_noun = extraction.get("main_noun")

    logger.info("🧠 Sustantivo extraído: %s", main_noun)

    if not main_noun or main_noun == "NONE":
        return {
            "query": user_message,
            "candidates": [],
            "top": [],
            "message": "No se pudo identificar el tema principal del aprendizaje."
        }

    # =====================================================
    # SEMANTIC GUARD (CLUSTERS)
    # =====================================================
    domain_eval = evaluate_domain(main_noun)

    if not domain_eval["allowed"]:
        return {
            "query": user_message,
            "candidates": [],
            "top": [],
            "message": f"No contamos con cursos relacionados con {main_noun} 😣💔. Intenta con otra busqueda"
        }

    logger.info(
        "Dominio Aprende aceptado | noun=%s | mode=%s | score=%.3f",
        main_noun,
        domain_eval.get("mode"),
        domain_eval.get("score", 0.0)
    )


    # =====================================================
    # BÚSQUEDA FINAL EN CLUSTERS
    # =====================================================
    candidates: List[Dict[str, Any]] = search_courses_in_clusters(user_message, k=k) or []

    logger.info(f"📊 Resultados de búsqueda: {len(candidates)} candidatos")

    top = candidates[:max(fetch_top_n, 0)] if candidates else []

    logger.info(f"✅ run_aprende_flow fin | candidatos={len(candidates)}, top={len(top)}")

    return {
        "query": user_message,
        "candidates": candidates,
        "top": top,
    }
