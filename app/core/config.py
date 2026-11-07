
import os
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    event_url: str = os.getenv(
        "EVENT_URL",
        "https://webook.com/en/events/rashed-almajed-concert-rs27-tickets-783777",
    )
    event_name: str = os.getenv(
        "EVENT_NAME",
        "Rashed Al Majid Concert",
    )
    ticket_release_at: str = os.getenv(
        "TICKET_RELEASE_AT",
        "2026-11-07T17:00:00+03:00",
    )
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    run_mode: str = os.getenv("RUN_MODE", "manual_assistant")


settings = Settings()


def validate_settings() -> None:
    parsed_url = urlparse(settings.event_url)

    if (
        parsed_url.scheme != "https"
        or parsed_url.hostname not in {"webook.com", "www.webook.com"}
        or parsed_url.username is not None
        or parsed_url.password is not None
        or parsed_url.port not in (None, 443)
    ):
        raise ValueError("EVENT_URL must be an official Webook HTTPS URL.")

    if settings.run_mode != "manual_assistant":
        raise ValueError(
            f"Unsupported RUN_MODE: {settings.run_mode}"
        )

    try:
        release_time = datetime.fromisoformat(settings.ticket_release_at)
        if release_time.tzinfo is None:
            raise ValueError
    except ValueError:
        raise ValueError(
            "TICKET_RELEASE_AT must include a date, time, and timezone offset."
        ) from None
