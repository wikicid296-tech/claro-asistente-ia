import os
import requests
from typing import Any, Dict


BASE_URL = os.getenv("APRENDE_API_URL", "https://aprende.org/api")


def fetch_course_by_id(course_id: str) -> Dict[str, Any]:
    url = f"{BASE_URL}/courses/{course_id}"

    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            return resp.json()
        return {"success": False, "error": "No encontrado"}
    except Exception as e:
        return {"success": False, "error": str(e)}
