from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_MAX_URLS = 3
DEFAULT_MAX_ELEMENTS = 15


def _extract_text_from_html(html: str, url: str) -> str:
    """
    Extrae texto semi-estructurado de una página HTML.
    Mantiene un formato ligero tipo 'resumen de contexto' útil para LLM.
    """
    soup = BeautifulSoup(html, "html.parser")

    # eliminar scripts/estilos
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text_elements: List[str] = []

    # encabezados
    for tag in ("h1", "h2", "h3"):
        for element in soup.find_all(tag):
            text = element.get_text(" ", strip=True)
            if text and len(text) > 5:
                text_elements.append(f"## {text}")

    # párrafos y listas
    for tag in ("p", "li"):
        for element in soup.find_all(tag):
            text = element.get_text(" ", strip=True)
            # heurística básica para evitar basura
            if text and 20 < len(text) < 500:
                text_elements.append(text)

    content = "\n".join(text_elements[:DEFAULT_MAX_ELEMENTS])

    if not content:
        return ""

    return f"=== CONTENIDO DE {url} ===\n{content}\n"


async def fetch_url(
    session: aiohttp.ClientSession,
    url: str,
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
) -> Optional[str]:
    """
    Descarga y extrae contenido textual relevante de una URL.
    Retorna None si falla o si no hay contenido útil.
    """
    try:
        timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        async with session.get(url, timeout=timeout) as response:
            if response.status != 200:
                logger.info(f"fetch_url status != 200: {url} ({response.status})")
                return None

            html = await response.text(errors="ignore")
            content = _extract_text_from_html(html, url)
            return content or None

    except asyncio.TimeoutError:
        logger.warning(f"Timeout fetching: {url}")
        return None
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return None


async def load_web_content_async(
    urls: List[str],
    *,
    max_urls: int = DEFAULT_MAX_URLS,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
) -> str:
    """
    Carga contenido de varias URLs en paralelo.
    Retorna un string concatenado con los bloques de contenido.
    """
    try:
        if not urls:
            return ""

        # Normalizar y recortar lista
        safe_urls = [u for u in urls if isinstance(u, str) and u.strip()]
        safe_urls = safe_urls[:max_urls]

        if not safe_urls:
            return ""

        async with aiohttp.ClientSession() as session:
            tasks = [
                fetch_url(session, url, timeout_seconds=timeout_seconds)
                for url in safe_urls
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        valid: List[str] = []
        for r in results:
            if isinstance(r, Exception):
                continue
            if isinstance(r, str) and r.strip():
                valid.append(r)

        return "\n".join(valid)

    except Exception as e:
        logger.error(f"Error in load_web_content_async: {e}")
        return ""
