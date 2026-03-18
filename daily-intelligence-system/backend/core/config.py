from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@db:5432/daily_intel"
    DB_USER: str = "daily_intel_user"
    DB_PASSWORD: str = "change_this_password"

    # Redis
    REDIS_URL: str = "redis://redis:6379"

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = ""

    # Telegram API (Telethon)
    TELEGRAM_API_ID: int = 0
    TELEGRAM_API_HASH: str = ""
    TELEGRAM_PHONE: str = ""

    # AI
    ANTHROPIC_API_KEY: str = ""
    AI_MODEL: str = "claude-sonnet-4-20250514"

    # Admin
    ADMIN_SECRET_KEY: str = "change_this_to_random_string"
    ADMIN_TELEGRAM_ID: int = 0

    # Scheduler
    MORNING_BRIEF_TIME: str = "07:30"
    MIDDAY_BRIEF_TIME: str = "12:30"
    EVENING_BRIEF_TIME: str = "18:30"
    PARSE_INTERVAL_MINUTES: int = 30

    # Rate limiting
    AI_MAX_REQUESTS_PER_SECOND: int = 2

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
