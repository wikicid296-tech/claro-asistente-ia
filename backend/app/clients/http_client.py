import logging
from typing import Dict, Any, Optional

import requests

logger = logging.getLogger(__name__)


DEFAULT_TIMEOUT = 10


class HttpClientError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


def http_get(
    url: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = DEFAULT_TIMEOUT
) -> Dict[str, Any]:
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=timeout)
        if not resp.ok:
            raise HttpClientError(
                f"GET failed: {url}",
                status_code=resp.status_code,
                payload=_safe_json(resp)
            )
        return _safe_json(resp)
    except requests.RequestException as e:
        logger.error(f"HTTP GET error: {e}")
        raise HttpClientError(str(e))


def http_post(
    url: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    timeout: int = DEFAULT_TIMEOUT
) -> Dict[str, Any]:
    try:
        resp = requests.post(url, headers=headers, json=json_body, data=data, timeout=timeout)
        if not resp.ok:
            raise HttpClientError(
                f"POST failed: {url}",
                status_code=resp.status_code,
                payload=_safe_json(resp)
            )
        return _safe_json(resp)
    except requests.RequestException as e:
        logger.error(f"HTTP POST error: {e}")
        raise HttpClientError(str(e))


def _safe_json(resp: requests.Response) -> Dict[str, Any]:
    try:
        return resp.json() if resp.content else {}
    except Exception:
        return {"raw": resp.text}
