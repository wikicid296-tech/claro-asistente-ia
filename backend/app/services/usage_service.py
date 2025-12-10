
import os
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Precios por 1M de tokens (USD)
GROQ_PRICES = {"input": 0.59, "output": 0.79}
OPENAI_PRICES = {"input": 2.50, "output": 10.00}

USAGE_LIMIT = float(os.getenv("USAGE_LIMIT", "10.00"))
WARNING_THRESHOLD = float(os.getenv("WARNING_THRESHOLD", "9.00"))


def get_usage_consumed() -> float:
    try:
        consumed = float(os.getenv("USAGE_CONSUMED", "0.00"))
        return round(consumed, 4)
    except Exception as e:
        logger.error(f"Error leyendo USAGE_CONSUMED: {e}")
        return 0.00


def set_usage_consumed(amount: float) -> None:
    # Nota: en producción esto solo vive en memoria del proceso.
    os.environ["USAGE_CONSUMED"] = str(round(amount, 4))
    logger.info(f"Consumo actualizado en memoria: ${amount:.4f}")


def add_usage(cost: float) -> float:
    current = get_usage_consumed()
    new_total = current + cost
    set_usage_consumed(new_total)
    logger.info(f"Costo agregado: ${cost:.6f} | Total: ${new_total:.4f}")
    return new_total


def calculate_cost(input_tokens: int, output_tokens: int, api_type: str = "groq") -> float:
    api_type = (api_type or "groq").lower()
    prices = GROQ_PRICES if api_type == "groq" else OPENAI_PRICES if api_type == "openai" else GROQ_PRICES

    input_cost = (input_tokens / 1_000_000) * prices["input"]
    output_cost = (output_tokens / 1_000_000) * prices["output"]
    total_cost = input_cost + output_cost

    logger.info(f"Tokens: {input_tokens} in + {output_tokens} out | Costo: ${total_cost:.6f} ({api_type})")
    return total_cost


def is_usage_blocked() -> bool:
    return get_usage_consumed() >= USAGE_LIMIT


def get_usage_status() -> dict:
    consumed = get_usage_consumed()
    percentage = (consumed / USAGE_LIMIT) * 100 if USAGE_LIMIT else 0
    blocked = consumed >= USAGE_LIMIT
    warning = consumed >= WARNING_THRESHOLD and not blocked

    return {
        "consumed": round(consumed, 2),
        "limit": round(USAGE_LIMIT, 2),
        "percentage": round(percentage, 1),
        "blocked": blocked,
        "warning": warning,
        "remaining": round(USAGE_LIMIT - consumed, 2),
    }
