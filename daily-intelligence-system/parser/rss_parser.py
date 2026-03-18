"""RSS/Atom feed parser — feedparser bilan."""
import asyncio
from datetime import datetime
from typing import Optional
import feedparser
from dateutil import parser as dateutil_parser
from loguru import logger
from parser.base_parser import BaseParser


class RSSParser(BaseParser):
    """RSS va Atom feedlarni o'qish uchun parser."""

    def __init__(self, source_id: int, source_url: str, source_name: str,
                 rss_url: str, language: str = "uz"):
        super().__init__(source_id, source_url, source_name)
        self.rss_url = rss_url
        self.language = language

    async def fetch(self) -> list[dict]:
        """RSS feeddan maqolalarni olish."""
        loop = asyncio.get_event_loop()
        feed = await loop.run_in_executor(None, feedparser.parse, self.rss_url)

        if feed.bozo and not feed.entries:
            logger.warning(f"[{self.source_name}] RSS parse error: {feed.bozo_exception}")
            return []

        articles = []
        for entry in feed.entries:
            try:
                article = self._parse_entry(entry)
                if article:
                    articles.append(article)
            except Exception as e:
                logger.warning(f"[{self.source_name}] Entry parse error: {e}")
                continue

        return articles

    def _parse_entry(self, entry: feedparser.FeedParserDict) -> Optional[dict]:
        """Bitta RSS entry'ni parse qilish."""
        title = getattr(entry, "title", "").strip()
        url = getattr(entry, "link", "").strip()

        if not title or not url:
            return None

        # Mazmun
        content = ""
        if hasattr(entry, "content") and entry.content:
            content = entry.content[0].get("value", "")
        elif hasattr(entry, "summary"):
            content = entry.summary
        elif hasattr(entry, "description"):
            content = entry.description

        if not content:
            content = title

        # Sana
        published_at = datetime.utcnow()
        for field in ["published_parsed", "updated_parsed", "created_parsed"]:
            parsed = getattr(entry, field, None)
            if parsed:
                try:
                    published_at = datetime(*parsed[:6])
                    break
                except Exception:
                    pass

        return self._build_article(title, url, content, published_at, self.language)
