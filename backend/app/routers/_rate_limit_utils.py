from __future__ import annotations

from typing import Callable, Any

# Intentamos importar el limiter real desde tu capa de extensions
try:
    from app.extensions import limiter  # type: ignore
except Exception:
    limiter = None  # type: ignore


def limit(rule: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorador seguro para rate limit.
    Si limiter existe, aplica limiter.limit(rule).
    Si no existe, deja la función intacta.
    """
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        if limiter:
            return limiter.limit(rule)(fn)
        return fn
    return decorator


def exempt(fn: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorador seguro para exentar endpoints.
    Si limiter existe, aplica limiter.exempt.
    Si no existe, deja la función intacta.
    """
    if limiter:
        return limiter.exempt(fn)
    return fn
