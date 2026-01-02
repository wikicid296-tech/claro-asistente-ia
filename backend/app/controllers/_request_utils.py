from flask import request

def get_user_key_from_request() -> str:
    return request.remote_addr or "unknown"
