import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Cargar .env una sola vez en el arranque de la app
load_dotenv()


@dataclass(frozen=True)
class Pricing:
    input: float
    output: float


# Precios por 1M tokens (USD)
GROQ_PRICES = Pricing(input=0.59, output=0.79)
OPENAI_PRICES = Pricing(input=2.50, output=10.00)


@dataclass(frozen=True)
class Settings:
    # Server
    PORT: int = int(os.getenv("PORT", "10000"))
    ENV: str = os.getenv("ENV", "production")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Rate limiting
    RATE_LIMIT_STORAGE_URI: str = os.getenv("RATE_LIMIT_STORAGE_URI", "memory://")
    DEFAULT_LIMITS: tuple = tuple(
        os.getenv("RATE_LIMIT_DEFAULTS", "200 per day,50 per hour").split(",")
    )

    # Cost tracking
    USAGE_LIMIT: float = float(os.getenv("USAGE_LIMIT", "10.00"))
    WARNING_THRESHOLD: float = float(os.getenv("WARNING_THRESHOLD", "9.00"))
    USAGE_CONSUMED_ENV_KEY: str = os.getenv("USAGE_CONSUMED_ENV_KEY", "USAGE_CONSUMED")

    # Providers
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    VECTOR_STORE_ID: str = os.getenv(
        "VECTOR_STORE_ID",
        "vs_6933017a9aa08191a0c0a728c78429cc"
    )

    # Twilio
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_WHATSAPP_NUMBER: str = os.getenv(
        "TWILIO_WHATSAPP_NUMBER",
        "whatsapp:+14155238886"
    )

    # Cursos API (para el siguiente paso del flujo Aprende)
    COURSES_API_BASE_URL: str = os.getenv("COURSES_API_BASE_URL", "")


settings = Settings()
