from app.services.task_service import delete_task_service

def delete_task_controller(task_id: str, user_key: str):
    tasks = delete_task_service(task_id, user_key)

    return {
        "success": True,
        "tasks": {
            "calendar": [t.__dict__ for t in tasks["calendar"]],
            "reminder": [t.__dict__ for t in tasks["reminder"]],
            "note": [t.__dict__ for t in tasks["note"]],
        }
    }
