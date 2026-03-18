"""Trend signallarni aniqlash."""
from collections import Counter
from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy import select, and_
from backend.core.database import AsyncSessionLocal
from database.models import Article


async def analyze_trends(hours: int = 24) -> list[dict]:
    """So'nggi N soatdagi maqolalardagi trendlarni aniqlash."""
    since = datetime.utcnow() - timedelta(hours=hours)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Article).where(
                and_(
                    Article.created_at >= since,
                    Article.is_duplicate == False,
                    Article.category != None,
                )
            )
        )
        articles = result.scalars().all()

    if not articles:
        return []

    # Kategoriya bo'yicha frekvens
    category_counter: Counter = Counter()
    entity_counter: Counter = Counter()

    for a in articles:
        if a.category:
            category_counter[a.category.value] += 1
        if a.entities:
            for company in a.entities.get("companies", []):
                entity_counter[company] += 1
            for person in a.entities.get("persons", []):
                entity_counter[person] += 1

    trends = []

    # Top 5 kategoriya
    for category, count in category_counter.most_common(5):
        if count >= 3:
            trends.append({
                "type": "category",
                "name": category,
                "count": count,
                "signal": "rising" if count >= 10 else "stable",
            })

    # Top 10 entity
    for entity, count in entity_counter.most_common(10):
        if count >= 3:
            trends.append({
                "type": "entity",
                "name": entity,
                "count": count,
                "signal": "spike" if count >= 5 else "mention",
            })

    logger.info(f"Found {len(trends)} trends in last {hours} hours")
    return trends
