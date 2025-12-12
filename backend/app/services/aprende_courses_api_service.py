from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
import logging
import requests

logger = logging.getLogger(__name__)


def get_aprende_api_base_url() -> Optional[str]:
    return os.getenv("APRENDE_API_BASE_URL")


def fetch_course_by_id(course_id: str) -> Dict[str, Any]:
    base = get_aprende_api_base_url()
    if not base:
        logger.warning("APRENDE_API_BASE_URL no configurado.")
        return {"success": False, "error": "APRENDE_API_BASE_URL no configurado"}

    try:
        url = f"{base.rstrip('/')}/courses/{course_id}"
        print(f"\n📡 LLAMANDO API: {url}")
        r = requests.get(url, timeout=12)
        r.raise_for_status()
        
        raw_data = r.json() if r.content else {}
        print(f"📦 RAW RESPONSE TYPE: {type(raw_data)}")
        print(f"📦 RAW RESPONSE KEYS: {list(raw_data.keys()) if isinstance(raw_data, dict) else 'Not a dict'}")
        
        # DIFERENTES FORMATOS POSIBLES:
        # 1. { "356": { "name": "...", ... } }  ← El que mostraste antes
        # 2. { "id": 356, "name": "...", ... }  ← El que veo en los logs
        
        course_data = None
        
        # Caso 1: La clave es el course_id como string
        if isinstance(raw_data, dict) and str(course_id) in raw_data:
            course_data = raw_data[str(course_id)]
            print(f"✅ Formato 1: datos bajo key '{course_id}'")
            
        # Caso 2: Es un objeto directo con 'id' field
        elif isinstance(raw_data, dict) and 'id' in raw_data:
            course_data = raw_data
            print(f"✅ Formato 2: objeto directo con id={course_data.get('id')}")
            
        # Caso 3: Primer objeto del dict
        elif isinstance(raw_data, dict) and len(raw_data) == 1:
            first_key = next(iter(raw_data))
            course_data = raw_data[first_key]
            print(f"⚠️ Formato 3: usando primera key '{first_key}'")
            
        else:
            course_data = raw_data
            print(f"ℹ️ Formato desconocido, usando raw_data")
        
        print(f"📊 COURSE_DATA TYPE: {type(course_data)}")
        if isinstance(course_data, dict):
            print(f"🔑 COURSE_DATA KEYS: {list(course_data.keys())}")
            print(f"🏷️  NAME FIELD: {course_data.get('name', 'NO NAME')}")
            print(f"📝 TITLE FIELD: {course_data.get('title', 'NO TITLE')}")
            print(f"🎓 COURSENAME FIELD: {course_data.get('courseName', 'NO COURSENAME')}")
        
        return {
            "success": True, 
            "data": course_data,
            "raw_response": raw_data  # Para debug
        }

    except Exception as e:
        print(f"❌ ERROR en API call: {e}")
        logger.error(f"Error fetch_course_by_id({course_id}): {e}", exc_info=True)
        return {"success": False, "error": str(e)}

def fetch_courses_top_candidates(candidates: List[Dict[str, Any]], max_fetch: int = 1) -> List[Dict[str, Any]]:
    """
    Recibe la lista de candidatos del vector search y enriquece
    con detalles de la API de cursos.
    Por defecto solo trae top1.
    """
    enriched: List[Dict[str, Any]] = []
    for c in candidates[:max_fetch]:
        course_id = str(c.get("courseId", ""))
        if not course_id:
            continue

        detail = fetch_course_by_id(course_id)
        enriched.append({
            **c,
            "detail": detail.get("data") if detail.get("success") else None,
            "detail_error": None if detail.get("success") else detail.get("error")
        })

    return enriched

def get_course_by_id(course_id: str) -> Optional[dict]:
    """
    Obtiene un curso directamente por ID desde la API Aprende.
    Retorna None si no existe.
    """
    try:
        course = fetch_course_by_id(course_id)
        if not course:
            return None

        return {
            "courseId": str(course.get("courseId") or course_id),
            "courseName": course.get("courseName") or "Curso disponible",
            "score": 1.0,
            "metadata": {
                "courseId": str(course.get("courseId") or course_id),
                "courseName": course.get("courseName"),
                "matchType": "explicit_id"
            }
        }
    except Exception:
        logger.exception("Error obteniendo curso por ID")
        return None