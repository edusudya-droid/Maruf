"""Barcha parserni boshqaruvchi manager."""
import asyncio
from loguru import logger
from sqlalchemy import select
from backend.core.database import AsyncSessionLocal
from database.models import Source, Article, SourceType
from parser.rss_parser import RSSParser
from parser.html_parser import HTMLParser
from parser.telegram_parser import TelegramParser
from processing.cleaner import clean_text
from processing.deduplicator import Deduplicator


class SourceManager:
    """Barcha manbalarga parse buyrug'ini yuboruvchi bosh manager."""

    def __init__(self):
        self.deduplicator = Deduplicator()

    async def run_all(self) -> int:
        """Barcha faol manbalarni parse qilish."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Source).where(Source.is_active == True)
            )
            sources = result.scalars().all()

        total_saved = 0
        tasks = [self._process_source(source) for source in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for idx, res in enumerate(results):
            if isinstance(res, Exception):
                logger.error(f"Source {sources[idx].name} failed: {res}")
            else:
                total_saved += res

        logger.info(f"Total new articles saved: {total_saved}")
        return total_saved

    async def _process_source(self, source: Source) -> int:
        """Bitta manbani parse qilib, yangi maqolalarni saqlash."""
        parser = self._build_parser(source)
        if not parser:
            return 0

        raw_articles = await parser.safe_fetch()
        if not raw_articles:
            return 0

        saved = 0
        async with AsyncSessionLocal() as session:
            for raw in raw_articles:
                try:
                    # Matnni tozalash
                    raw["content"] = clean_text(raw["content"])
                    raw["title"] = clean_text(raw["title"])

                    if len(raw["content"]) < 50:
                        continue

                    # Dublikat tekshirish (URL bo'yicha)
                    exists = await session.execute(
                        select(Article).where(Article.url == raw["url"])
                    )
                    if exists.scalar_one_or_none():
                        continue

                    article = Article(**raw)
                    session.add(article)
                    saved += 1

                except Exception as e:
                    logger.warning(f"[{source.name}] Article save error: {e}")
                    continue

            await session.commit()

        # Update last_checked_at
        async with AsyncSessionLocal() as session:
            result = await session.get(Source, source.id)
            if result:
                from datetime import datetime
                result.last_checked_at = datetime.utcnow()
                await session.commit()

        return saved

    def _build_parser(self, source: Source):
        """Manba turiga qarab tegishli parser yaratish."""
        if source.source_type == SourceType.rss and source.rss_url:
            return RSSParser(source.id, source.url, source.name, source.rss_url, source.language)
        elif source.source_type == SourceType.html:
            return HTMLParser(source.id, source.url, source.name, language=source.language)
        elif source.source_type == SourceType.telegram and source.telegram_channel:
            return TelegramParser(source.id, source.url, source.name,
                                  source.telegram_channel, source.language)
        else:
            logger.warning(f"[{source.name}] Unknown source type: {source.source_type}")
            return None


async def main():
    manager = SourceManager()
    await manager.run_all()


if __name__ == "__main__":
    asyncio.run(main())
