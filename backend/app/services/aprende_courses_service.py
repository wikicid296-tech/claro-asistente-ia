from __future__ import annotations

from typing import Any, Dict, List

from app.clients.aprende_api_client import fetch_course_by_id


def enrich_candidates_with_course_details(
    candidates: List[Dict[str, Any]],
    max_fetch: int = 1
) -> List[Dict[str, Any]]:
    """
    Enriquecer candidatos del vector search con detalles de la API.
    Por defecto solo top1.
    """
    enriched: List[Dict[str, Any]] = []

    for c in candidates[:max_fetch]:
        course_id = str(c.get("courseId", "") or "")
        if not course_id:
            continue

        detail = fetch_course_by_id(course_id)

        enriched.append({
            **c,
            "detail": detail.get("data") if detail.get("success") else None,
            "detail_error": detail.get("error") if not detail.get("success") else None,
        })

    return enriched
