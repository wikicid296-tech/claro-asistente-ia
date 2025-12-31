import time
from typing import Dict
from app.states.conversationState import ConversationState

_CACHE: Dict[str, ConversationState] = {}
TTL_SECONDS = 300  # 5 minutos

print("🔥 conversationStore LOADED", id(globals()))

def load_state(user_key: str) -> ConversationState:
    print("📤 load_state:", user_key)
    if not user_key:
        return ConversationState()

    state = _CACHE.get(user_key)
    if not state:
        return ConversationState()

    if time.time() - state.updated_at > TTL_SECONDS:
        _CACHE.pop(user_key, None)
        return ConversationState()

    return state


def save_state(user_key: str, state: ConversationState):
    print("💾 save_state:", user_key, state)

    if not user_key:
        return
    state.updated_at = time.time()
    _CACHE[user_key] = state


def clear_state(user_key: str):
    if not user_key:
        return
    _CACHE.pop(user_key, None)
