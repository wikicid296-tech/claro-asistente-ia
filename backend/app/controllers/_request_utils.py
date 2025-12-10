from flask import request


def get_user_key_from_request() -> str:
    ip = request.remote_addr or "unknown"
    ua = request.headers.get("User-Agent", "")
    return f"{ip}:{ua}"
