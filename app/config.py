from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    admin_key: str
    office_start: str = "09:00"
    grace_minutes: int = 15
    half_day_hours: float = 4.0
    timezone: str = "Asia/Karachi"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


settings = Settings()


def get_now() -> datetime:
    return datetime.now(
        ZoneInfo(settings.timezone)
    )