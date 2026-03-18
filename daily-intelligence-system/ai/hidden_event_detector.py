"""Yashirin voqealarni aniqlash — zaif signallarni kuzatish."""
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy import select, and_
from backend.core.database import AsyncSessionLocal
from database.models import Article, Event, ImpactLevel, ArticleCategory, EventPriority


HIDDEN_EVENT_THRESHOLD = 60  # Bu va undan yuqori ball = ehtimoliy yashirin voqea
EMERGING_THRESHOLD = 40       # Bu va undan yuqori = kuzatish


async def detect_hidden_events() -> list[dict]:
    """Oxirgi 6-24 soatdagi signallardan yashirin voqealarni aniqlash."""
    now = datetime.utcnow()
    since_6h = now - timedelta(hours=6)
    since_24h = now - timedelta(hours=24)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Article).where(
                and_(
                    Article.created_at >= since_24h,
                    Article.is_duplicate == False,
                    Article.is_processed == True,
                )
            )
        )
        articles = result.scalars().all()

    if not articles:
        return []

    # Entity bo'yicha guruhlash
    entity_groups: dict[str, list[Article]] = defaultdict(list)

    for a in articles:
        if not a.entities:
            continue
        for entity_type in ["companies", "persons", "projects"]:
            for entity_name in a.entities.get(entity_type, []):
                if entity_name and len(entity_name) > 3:
                    entity_groups[entity_name].append(a)

    signals = []

    for entity_name, entity_articles in entity_groups.items():
        if len(entity_articles) < 3:
            continue

        # Manba turlari soni
        source_types = set()
        for a in entity_articles:
            if hasattr(a, "source") and a.source:
                source_types.add(a.source.source_type.value)

        if len(source_types) < 2:
            continue  # Kamida 2 turdagi manba kerak

        # O'sish tendensiyasi
        recent_6h = [a for a in entity_articles if a.created_at >= since_6h]
        growth_rate = len(recent_6h) / max(len(entity_articles), 1)

        # Hidden Event Score hisoblash
        signal_frequency = min(len(entity_articles) * 5, 30)
        cross_source = min(len(source_types) * 10, 20)
        entity_spike = 15 if len(entity_articles) >= 5 else 10
        trend_growth = min(int(growth_rate * 20), 20)

        # Manba ishonchliligi
        avg_tier = 3
        tiered = [a for a in entity_articles if hasattr(a, "source") and a.source]
        if tiered:
            avg_tier = sum(a.source.tier for a in tiered) / len(tiered)
        source_reliability = max(0, 15 - int(avg_tier * 3))

        hidden_score = (
            signal_frequency + cross_source + entity_spike +
            trend_growth + source_reliability
        )

        if hidden_score < EMERGING_THRESHOLD:
            continue

        confidence = "low"
        if hidden_score >= HIDDEN_EVENT_THRESHOLD:
            confidence = "medium"
        if hidden_score >= 80:
            confidence = "high"

        signal = {
            "entity": entity_name,
            "article_count": len(entity_articles),
            "source_types": list(source_types),
            "hidden_score": round(hidden_score, 1),
            "confidence": confidence,
            "title": f"Signal: {entity_name} atrofida aktivlik kuzatilmoqda",
            "description": (
                f"{len(entity_articles)} ta manba {entity_name} haqida "
                f"{len(source_types)} turdagi manba orqali xabar bermoqda. "
                f"O'sish sur'ati: {int(growth_rate * 100)}%"
            ),
        }

        signals.append(signal)

        # Yuqori scoreli signallarni Event sifatida saqlash
        if hidden_score >= HIDDEN_EVENT_THRESHOLD:
            await _save_as_hidden_event(signal, entity_articles)

    signals.sort(key=lambda x: x["hidden_score"], reverse=True)
    logger.info(f"Detected {len(signals)} hidden event signals")
    return signals[:10]  # Top 10


async def _save_as_hidden_event(signal: dict, articles: list[Article]) -> None:
    """Yashirin voqeani Event jadvaliga saqlash."""
    async with AsyncSessionLocal() as session:
        from database.models import EventArticle, ArticleRole
        event = Event(
            title=signal["title"],
            description=signal["description"],
            category=ArticleCategory.risk,
            priority=EventPriority.medium,
            event_score=signal["hidden_score"],
            is_hidden_event=True,
            hidden_event_score=signal["hidden_score"],
            impact_level=ImpactLevel.national,
            source_count=signal["article_count"],
            entities={"entity": signal["entity"]},
        )
        session.add(event)
        await session.flush()

        for idx, article in enumerate(articles[:5]):
            role = ArticleRole.primary if idx == 0 else ArticleRole.supporting
            ea = EventArticle(event_id=event.id, article_id=article.id, role=role)
            session.add(ea)

        await session.commit()
        logger.info(f"Saved hidden event: {signal['title'][:60]}")
