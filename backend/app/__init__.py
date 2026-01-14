# backend/app/__init__.py
from flask import Flask
from flask_cors import CORS

from app.routers.system_routes import system_bp
from app.routers.chat_routes import chat_bp
from app.routers.webhook_routes import webhook_bp
from app.routers.calendar_routes import calendar_bp
from app.routers.static_routes import static_bp

from app.routers.error_handlers import register_error_handlers


def create_app():
    app = Flask(__name__)
    CORS(app)

    # Blueprints
    app.register_blueprint(system_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(webhook_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(static_bp)

    # Error handlers centralizados
    register_error_handlers(app)

    return app
