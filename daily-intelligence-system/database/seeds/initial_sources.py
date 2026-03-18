"""Boshlang'ich manbalar ro'yxatini bazaga yuklash."""
import asyncio
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.core.database import AsyncSessionLocal
from database.models import Source, SourceType, SourceCategory


INITIAL_SOURCES = [
    # O'zbekiston SMI
    {
        "name": "Kun.uz", "url": "https://kun.uz",
        "rss_url": "https://kun.uz/rss", "source_type": SourceType.rss,
        "category": SourceCategory.news, "tier": 1, "trust_score": 0.9,
        "language": "uz", "country": "UZ", "priority": 10,
    },
    {
        "name": "Daryo.uz", "url": "https://daryo.uz",
        "rss_url": "https://daryo.uz/feed", "source_type": SourceType.rss,
        "category": SourceCategory.news, "tier": 1, "trust_score": 0.9,
        "language": "uz", "country": "UZ", "priority": 10,
    },
    {
        "name": "Gazeta.uz", "url": "https://gazeta.uz",
        "rss_url": "https://gazeta.uz/rss", "source_type": SourceType.rss,
        "category": SourceCategory.news, "tier": 1, "trust_score": 0.9,
        "language": "uz", "country": "UZ", "priority": 9,
    },
    {
        "name": "Qalampir.uz", "url": "https://qalampir.uz",
        "rss_url": "https://qalampir.uz/rss", "source_type": SourceType.rss,
        "category": SourceCategory.news, "tier": 1, "trust_score": 0.85,
        "language": "uz", "country": "UZ", "priority": 9,
    },
    {
        "name": "Spot.uz", "url": "https://spot.uz",
        "rss_url": "https://spot.uz/rss", "source_type": SourceType.rss,
        "category": SourceCategory.analytics, "tier": 2, "trust_score": 0.8,
        "language": "uz", "country": "UZ", "priority": 8,
    },
    {
        "name": "Review.uz", "url": "https://review.uz",
        "rss_url": "https://review.uz/rss", "source_type": SourceType.rss,
        "category": SourceCategory.analytics, "tier": 2, "trust_score": 0.8,
        "language": "uz", "country": "UZ", "priority": 8,
    },
    {
        "name": "Norma.uz", "url": "https://norma.uz",
        "source_type": SourceType.html,
        "category": SourceCategory.legal, "tier": 1, "trust_score": 0.95,
        "language": "uz", "country": "UZ", "priority": 10,
    },
    {
        "name": "UzA.uz", "url": "https://uza.uz",
        "rss_url": "https://uza.uz/rss", "source_type": SourceType.rss,
        "category": SourceCategory.news, "tier": 1, "trust_score": 0.85,
        "language": "uz", "country": "UZ", "priority": 9,
    },
    {
        "name": "Anhor.uz", "url": "https://anhor.uz",
        "rss_url": "https://anhor.uz/rss", "source_type": SourceType.rss,
        "category": SourceCategory.news, "tier": 2, "trust_score": 0.75,
        "language": "uz", "country": "UZ", "priority": 7,
    },
    # Davlat saytlari
    {
        "name": "Lex.uz", "url": "https://lex.uz",
        "source_type": SourceType.html,
        "category": SourceCategory.legal, "tier": 1, "trust_score": 1.0,
        "language": "uz", "country": "UZ", "priority": 10,
    },
    {
        "name": "President.uz", "url": "https://president.uz",
        "source_type": SourceType.html,
        "category": SourceCategory.gov, "tier": 1, "trust_score": 1.0,
        "language": "uz", "country": "UZ", "priority": 10,
    },
    {
        "name": "Gov.uz", "url": "https://gov.uz",
        "source_type": SourceType.html,
        "category": SourceCategory.gov, "tier": 1, "trust_score": 1.0,
        "language": "uz", "country": "UZ", "priority": 10,
    },
    {
        "name": "MinEconomy", "url": "https://mineconomy.uz",
        "source_type": SourceType.html,
        "category": SourceCategory.gov, "tier": 1, "trust_score": 0.95,
        "language": "uz", "country": "UZ", "priority": 9,
    },
    {
        "name": "MinFin", "url": "https://minfin.uz",
        "source_type": SourceType.html,
        "category": SourceCategory.gov, "tier": 1, "trust_score": 0.95,
        "language": "uz", "country": "UZ", "priority": 9,
    },
    {
        "name": "Markaziy bank", "url": "https://centralbank.uz",
        "source_type": SourceType.html,
        "category": SourceCategory.economic, "tier": 1, "trust_score": 1.0,
        "language": "uz", "country": "UZ", "priority": 10,
    },
    {
        "name": "Statistika", "url": "https://statistics.uz",
        "source_type": SourceType.html,
        "category": SourceCategory.economic, "tier": 1, "trust_score": 1.0,
        "language": "uz", "country": "UZ", "priority": 9,
    },
    {
        "name": "Soliq", "url": "https://soliq.uz",
        "source_type": SourceType.html,
        "category": SourceCategory.legal, "tier": 1, "trust_score": 0.95,
        "language": "uz", "country": "UZ", "priority": 9,
    },
    {
        "name": "Senate", "url": "https://senate.uz",
        "source_type": SourceType.html,
        "category": SourceCategory.gov, "tier": 1, "trust_score": 1.0,
        "language": "uz", "country": "UZ", "priority": 9,
    },
    # Telegram kanallar
    {
        "name": "Kun.uz Telegram", "url": "https://t.me/kunuzofficial",
        "telegram_channel": "@kunuzofficial", "source_type": SourceType.telegram,
        "category": SourceCategory.news, "tier": 1, "trust_score": 0.9,
        "language": "uz", "country": "UZ", "priority": 10,
    },
    {
        "name": "Daryo Telegram", "url": "https://t.me/daryo",
        "telegram_channel": "@daryo", "source_type": SourceType.telegram,
        "category": SourceCategory.news, "tier": 1, "trust_score": 0.9,
        "language": "uz", "country": "UZ", "priority": 10,
    },
    {
        "name": "Gazeta.uz Telegram", "url": "https://t.me/gazetauz",
        "telegram_channel": "@gazetauz", "source_type": SourceType.telegram,
        "category": SourceCategory.news, "tier": 1, "trust_score": 0.9,
        "language": "uz", "country": "UZ", "priority": 9,
    },
    {
        "name": "Spot.uz Telegram", "url": "https://t.me/spotuz",
        "telegram_channel": "@spotuz", "source_type": SourceType.telegram,
        "category": SourceCategory.analytics, "tier": 2, "trust_score": 0.8,
        "language": "uz", "country": "UZ", "priority": 8,
    },
    {
        "name": "Finans.uz Telegram", "url": "https://t.me/finansuz",
        "telegram_channel": "@finansuz", "source_type": SourceType.telegram,
        "category": SourceCategory.economic, "tier": 2, "trust_score": 0.75,
        "language": "uz", "country": "UZ", "priority": 8,
    },
    {
        "name": "Norma.uz Telegram", "url": "https://t.me/norma_uz",
        "telegram_channel": "@norma_uz", "source_type": SourceType.telegram,
        "category": SourceCategory.legal, "tier": 2, "trust_score": 0.85,
        "language": "uz", "country": "UZ", "priority": 8,
    },
    {
        "name": "BBC Russian Telegram", "url": "https://t.me/bbcrussian",
        "telegram_channel": "@bbcrussian", "source_type": SourceType.telegram,
        "category": SourceCategory.international, "tier": 3, "trust_score": 0.9,
        "language": "ru", "country": "GB", "priority": 7,
    },
    # Xalqaro manbalar
    {
        "name": "Reuters", "url": "https://reuters.com",
        "rss_url": "https://feeds.reuters.com/reuters/topNews",
        "source_type": SourceType.rss,
        "category": SourceCategory.international, "tier": 1, "trust_score": 0.95,
        "language": "en", "country": "US", "priority": 9,
    },
    {
        "name": "BBC News", "url": "https://bbc.com",
        "rss_url": "http://feeds.bbci.co.uk/news/rss.xml",
        "source_type": SourceType.rss,
        "category": SourceCategory.international, "tier": 1, "trust_score": 0.95,
        "language": "en", "country": "GB", "priority": 9,
    },
    {
        "name": "World Bank", "url": "https://worldbank.org",
        "rss_url": "https://blogs.worldbank.org/rss.xml",
        "source_type": SourceType.rss,
        "category": SourceCategory.international, "tier": 1, "trust_score": 0.95,
        "language": "en", "country": "US", "priority": 8,
    },
    {
        "name": "IMF", "url": "https://imf.org",
        "rss_url": "https://imf.org/rss",
        "source_type": SourceType.rss,
        "category": SourceCategory.international, "tier": 1, "trust_score": 0.95,
        "language": "en", "country": "US", "priority": 8,
    },
]


async def seed_sources() -> None:
    async with AsyncSessionLocal() as session:
        for source_data in INITIAL_SOURCES:
            result = await session.execute(
                select(Source).where(Source.url == source_data["url"])
            )
            existing = result.scalar_one_or_none()
            if existing:
                logger.info(f"Source already exists: {source_data['name']}")
                continue

            source = Source(**source_data)
            session.add(source)
            logger.info(f"Added source: {source_data['name']}")

        await session.commit()
        logger.info(f"Seeded {len(INITIAL_SOURCES)} sources")


if __name__ == "__main__":
    asyncio.run(seed_sources())
