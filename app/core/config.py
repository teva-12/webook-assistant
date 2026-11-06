import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    event_url: str = os.getenv("EVENT_URL", "")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    run_mode: str = os.getenv("RUN_MODE", "manual_assistant")


settings = Settings()


def validate_settings() -> None:
    allowed_modes = {"manual_assistant"}

    if settings.run_mode not in allowed_modes:
        raise ValueError(
            f"Unsupported RUN_MODE: {settings.run_mode}"
        )

    if not settings.event_url.startswith("https://webook.com/"):
        raise ValueError("EVENT_URL must be a valid Webook HTTPS URL.")