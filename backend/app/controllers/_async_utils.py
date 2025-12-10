import asyncio
from typing import Any, Coroutine


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    """
    Ejecuta un coroutine en contexto sync.
    En Flask WSGI usualmente no hay loop activo.
    """
    try:
        return asyncio.run(coro)
    except RuntimeError:
        # Si por alguna razón hay un loop activo (poco común aquí),
        # usamos create_task y esperamos.
        loop = asyncio.get_event_loop()
        task = loop.create_task(coro)
        return loop.run_until_complete(task)
