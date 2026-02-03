from flask import Blueprint, request, jsonify
from app.controllers.task_controller import delete_task_controller

task_bp = Blueprint("task_router", __name__)


@task_bp.route("/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id: str):
    """
    Eliminación física de una tarea por ID.
    Requiere user_key (puede venir por header, query o sesión).
    """

    # 🔐 Ajusta esta parte según cómo manejes auth
    user_key = (
        request.headers.get("X-User-Key")
        or request.args.get("user_key")
    )

    if not user_key:
        return jsonify({
            "success": False,
            "error": "user_key es requerido"
        }), 400

    result = delete_task_controller(
        task_id=task_id,
        user_key=user_key
    )

    return jsonify(result), 200
