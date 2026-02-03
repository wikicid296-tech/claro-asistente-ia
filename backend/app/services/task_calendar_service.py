from app.services.calendar_ics import crear_invitacion_ics
from app.domain.task import Task


def generate_ics_for_task(task: Task) -> dict | None:
    """
    Genera ICS solo si la tarea tiene fecha y hora válidas.
    Nunca lanza excepción (fail-safe).
    """

    if not task.fecha or not task.hora:
        return None

    ics_content = crear_invitacion_ics(
        titulo=task.content,
        descripcion=task.description or task.content,
        fecha=str(task.fecha),
        hora=str(task.hora),
    )

    return {
        "ics_content": ics_content,
        "filename": f"evento_{task.fecha}_{task.hora}.ics",
    }