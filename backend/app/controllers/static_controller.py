import logging
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)


def _resolve_frontend_dir() -> Path:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[3] / "frontend",  # repo_root/frontend
        here.parents[2] / "frontend",  # backend/frontend
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


FRONTEND_DIR = _resolve_frontend_dir()


def serve_frontend():
    try:
        index_path = FRONTEND_DIR / "index.html"
        return index_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Error sirviendo index.html: {e}")
        return f"Error: {str(e)}", 500


def serve_images(filename: str) -> Tuple[bytes, int, dict]:
    try:
        img_path = FRONTEND_DIR / "images" / filename
        content = img_path.read_bytes()

        content_type = "image/png"
        lower = filename.lower()
        if lower.endswith(".jpg") or lower.endswith(".jpeg"):
            content_type = "image/jpeg"
        elif lower.endswith(".svg"):
            content_type = "image/svg+xml"
        elif lower.endswith(".webp"):
            content_type = "image/webp"

        return content, 200, {"Content-Type": content_type}

    except FileNotFoundError:
        logger.error(f"Imagen no encontrada: {filename}")
        return b"Imagen no encontrada", 404, {"Content-Type": "text/plain"}

    except Exception as e:
        logger.error(f"Error sirviendo imagen {filename}: {e}")
        return b"Error sirviendo imagen", 500, {"Content-Type": "text/plain"}


def serve_static(path: str):
    try:
        target = FRONTEND_DIR / path

        if path.startswith("styles/"):
            return target.read_text(encoding="utf-8"), 200, {"Content-Type": "text/css"}

        if path.startswith("js/"):
            return target.read_text(encoding="utf-8"), 200, {"Content-Type": "application/javascript"}

        return target.read_text(encoding="utf-8")

    except FileNotFoundError:
        logger.error(f"Archivo no encontrado: {path}")
        return f"Archivo no encontrado: {path}", 404

    except Exception as e:
        logger.error(f"Error sirviendo {path}: {e}")
        return f"Error sirviendo archivo: {path}", 500
