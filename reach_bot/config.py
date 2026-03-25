from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )

    # Bot
    bot_token: str = Field(..., alias="BOT_TOKEN")

    # Official channel
    official_channel_id: int = Field(..., alias="OFFICIAL_CHANNEL_ID")
    official_channel_url: str = Field(..., alias="OFFICIAL_CHANNEL_URL")

    # Database
    database_url: str = Field(..., alias="DATABASE_URL")

    # Redis / Celery
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(default="redis://redis:6379/0", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://redis:6379/1", alias="CELERY_RESULT_BACKEND")

    # Business rules
    similarity_threshold: float = Field(default=0.90, alias="SIMILARITY_THRESHOLD")
    retry_limit: int = Field(default=2, alias="RETRY_LIMIT")
    max_daily_analyses: int = Field(default=20, alias="MAX_DAILY_ANALYSES")
    max_visible_posts: int = Field(default=20, alias="MAX_VISIBLE_POSTS")
    max_users: int = Field(default=50)

    # Telethon (MTProto user client) — ixtiyoriy.
    # Olish: https://my.telegram.org → API development tools
    telegram_api_id: Optional[int] = Field(default=None, alias="TELEGRAM_API_ID")
    telegram_api_hash: Optional[str] = Field(default=None, alias="TELEGRAM_API_HASH")
    # Session string: bir marta generate_session.py orqali olinadi
    telethon_session: Optional[str] = Field(default=None, alias="TELETHON_SESSION")


settings = Settings()
