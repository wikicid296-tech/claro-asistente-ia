# backend/app/routers/calendar_routes.py
from flask import Blueprint

from app.controllers.calendar_controller import calendar_create_ics_controller

calendar_bp = Blueprint("calendar", __name__)

calendar_bp.route("/calendar/ics", methods=["POST"])(calendar_create_ics_controller)
