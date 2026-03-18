"""Telegram parser — telethon bilan kanallarni o'qish."""
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger
from parser.base_parser import BaseParser
from backend.core.config import settings


class TelegramParser(BaseParser):
    """Telegram kanallardan xabarlar o'quvchi parser."""

    def __init__(self, source_id: int, source_url: str, source_name: str,
                 channel: str, language: str = "uz"):
        super().__init__(source_id, source_url, source_name)
        self.channel = channel
        self.language = language
        self._client = None

    async def _get_client(self):
        """Telethon client yaratish yoki mavjudini qaytarish."""
        if self._client is None:
            try:
                from telethon import TelegramClient
                self._client = TelegramClient(
                    f"session_{self.channel.replace('@', '')}",
                    settings.TELEGRAM_API_ID,
                    settings.TELEGRAM_API_HASH,
                )
                await self._client.start(phone=settings.TELEGRAM_PHONE)
            except Exception as e:
                logger.error(f"Telethon client error: {e}")
                self._client = None
        return self._client

    async def fetch(self) -> list[dict]:
        """Telegram kanaldan so'nggi xabarlarni olish."""
        client = await self._get_client()
        if not client:
            logger.warning(f"[{self.source_name}] Telethon not available, skipping")
            return []

        articles = []
        try:
            since = datetime.utcnow() - timedelta(hours=24)
            async for message in client.iter_messages(self.channel, limit=50):
                if not message.text or len(message.text) < 50:
                    continue
                if message.date.replace(tzinfo=None) < since:
                    break

                # Repost bo'lsa o'tkazib yuborish
                if message.forward:
                    continue

                title = message.text[:100].split("\n")[0].strip()
                if not title:
                    continue

                url = f"https://t.me/{self.channel.replace('@', '')}/{message.id}"
                article = self._build_article(
                    title=title,
                    url=url,
                    content=message.text,
                    published_at=message.date.replace(tzinfo=None),
                    language=self.language,
                )
                articles.append(article)

        except Exception as e:
            logger.error(f"[{self.source_name}] Telegram fetch error: {e}")

        return articles
