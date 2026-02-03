# backend/app/__init__.py
from flask import Flask
from flask_cors import CORS

from app.routers.system_routes import system_bp
from app.routers.chat_routes import chat_bp
from app.routers.webhook_routes import webhook_bp
from app.routers.calendar_routes import calendar_bp
from app.routers.static_routes import static_bp

from app.routers.error_handlers import register_error_handlers
from app.routers.task_router import task_bp


def create_app():
    app = Flask(__name__)
    CORS(app)
    import logging
    import sys

    logging.basicConfig(
        level=logging.INFO,          # 👈 CLAVE
        format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    # Blueprints
    app.register_blueprint(system_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(webhook_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(static_bp)
    app.register_blueprint(task_bp, url_prefix="/api")
    # Error handlers centralizados
    register_error_handlers(app)

    return app
