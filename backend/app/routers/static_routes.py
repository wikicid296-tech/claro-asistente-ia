from flask import Blueprint

from app.controllers.static_controller import (
    serve_frontend,
    serve_images,
    serve_static,
)
from app.routers._rate_limit_utils import exempt

static_bp = Blueprint("static", __name__)

static_bp.route("/", methods=["GET"])(exempt(serve_frontend))
static_bp.route("/images/<path:filename>", methods=["GET"])(exempt(serve_images))
static_bp.route("/<path:path>", methods=["GET"])(exempt(serve_static))
