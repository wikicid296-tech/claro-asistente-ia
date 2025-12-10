from .system_routes import system_bp
from .chat_routes import chat_bp
from .webhook_routes import webhook_bp
from .calendar_routes import calendar_bp
from .static_routes import static_bp

__all__ = [
    "system_bp",
    "chat_bp",
    "webhook_bp",
    "calendar_bp",
    "static_bp",
]
