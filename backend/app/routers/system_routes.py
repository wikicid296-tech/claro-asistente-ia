# backend/app/routers/system_routes.py
from flask import Blueprint

from app.controllers.system_controller import (
    health_controller,
    usage_controller,
    urls_controller,
)

from app.routers._rate_limit_utils import exempt

system_bp = Blueprint("system", __name__)

system_bp.route("/health", methods=["GET"])(exempt(health_controller))
system_bp.route("/usage", methods=["GET"])(exempt(usage_controller))
system_bp.route("/urls", methods=["POST"])(urls_controller)
