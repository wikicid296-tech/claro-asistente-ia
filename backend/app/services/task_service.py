from app.stores.task_store import delete_task_by_id, get_tasks_grouped

def delete_task_service(task_id: str, user_key: str):
    delete_task_by_id(task_id, user_key)
    return get_tasks_grouped(user_key)
