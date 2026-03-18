"""Asosiy parser klassi — barcha parserlar shu klassdan meros oladi."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from loguru import logger


class BaseParser(ABC):
    """Barcha parser turlari uchun asosiy interfeys."""

    def __init__(self, source_id: int, source_url: str, source_name: str):
        self.source_id = source_id
        self.source_url = source_url
        self.source_name = source_name

    @abstractmethod
    async def fetch(self) -> list[dict]:
        """Manbadan maqolalar ro'yxatini olish."""
        ...

    def _build_article(
        self,
        title: str,
        url: str,
        content: str,
        published_at: datetime,
        language: str = "uz",
    ) -> dict:
        """Standart maqola dict yaratish."""
        return {
            "source_id": self.source_id,
            "title": title.strip(),
            "url": url.strip(),
            "content": content.strip(),
            "published_at": published_at,
            "language": language,
            "is_duplicate": False,
            "is_processed": False,
        }

    async def safe_fetch(self) -> list[dict]:
        """Xatolarni tutib, xavfsiz ravishda fetch qilish."""
        try:
            articles = await self.fetch()
            logger.info(f"[{self.source_name}] Fetched {len(articles)} articles")
            return articles
        except Exception as e:
            logger.error(f"[{self.source_name}] Fetch failed: {e}")
            return []
