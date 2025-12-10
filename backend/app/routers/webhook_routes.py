# backend/app/routers/webhook_routes.py
from flask import Blueprint

from app.controllers.webhooks_controller import (
    whatsapp_controller,
    sms_controller,
    rcs_controller,
    rcs_status_controller,
)

from app.routers._rate_limit_utils import limit, exempt

webhook_bp = Blueprint("webhooks", __name__)

webhook_bp.route("/whatsapp", methods=["POST"])(
    limit("20 per minute")(
        limit("1 per 2 seconds")(whatsapp_controller)
    )
)

webhook_bp.route("/sms", methods=["POST"])(
    limit("20 per minute")(
        limit("1 per 2 seconds")(sms_controller)
    )
)

webhook_bp.route("/rcs", methods=["POST", "GET"])(
    limit("20 per minute")(
        limit("1 per 2 seconds")(rcs_controller)
    )
)

webhook_bp.route("/rcs/status", methods=["POST"])(exempt(rcs_status_controller))
