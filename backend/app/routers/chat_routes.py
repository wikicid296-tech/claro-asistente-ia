# backend/app/routers/chat_routes.py
from flask import Blueprint

from app.controllers.chat_controller import chat_controller
from app.routers._rate_limit_utils import limit

chat_bp = Blueprint("chat", __name__)

chat_bp.route("/chat", methods=["POST"])(
    limit("10 per minute")(
        limit("1 per 3 seconds")(chat_controller)
    )
)
