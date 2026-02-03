from typing import Dict, List
from app.domain.task import Task

_TASKS: Dict[str, List[Task]] = {}

def add_task(task: Task):
    _TASKS.setdefault(task.user_key, []).append(task)

def get_tasks(user_key: str) -> List[Task]:
    return _TASKS.get(user_key, [])
def get_tasks_grouped(user_key: str) -> Dict[str, List[Task]]:
    tasks = get_tasks(user_key)
    return {
        "calendar": [t for t in tasks if t.type == "calendar"],
        "reminder": [t for t in tasks if t.type == "reminder"],
        "note": [t for t in tasks if t.type == "note"],
    }

def get_tasks_by_type(user_key: str, ttype: str) -> List[Task]:
    return [t for t in get_tasks(user_key) if t.type == ttype]

def get_active_tasks(user_key: str) -> List[Task]:
    return [t for t in get_tasks(user_key) if t.status == "active"]

def delete_task_by_id(task_id: str, user_key: str):
    tasks = _TASKS.get(user_key, [])
    filtered = [
        t for t in tasks
        if not (t.id == task_id and t.user_key == user_key)
    ]
    if filtered:
        _TASKS[user_key] = filtered
    else:
        _TASKS.pop(user_key, None)


def clear_tasks(user_key: str):
    _TASKS.pop(user_key, None)
