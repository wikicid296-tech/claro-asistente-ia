from flask import request

def get_user_key_from_request() -> str:
    conversation_id = request.headers.get("X-Conversation-Id")
    if conversation_id:
        return conversation_id

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    return request.remote_addr or "unknown"
