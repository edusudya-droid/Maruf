"""Voqealarni aniqlash va birlashtirish."""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger
from sqlalchemy import select, and_
from backend.core.database import AsyncSessionLocal
from database.models import Article, Event, EventArticle, ArticleCategory, ImpactLevel, EventPriority
from ai.event_scorer import calculate_event_score

SYSTEM_PROMPT = """Sen voqealar tahlilchisisanki, bir xil mavzu haqida yozilgan
bir nechta yangilikdan bitta voqea yarata olasan.

Berilgan maqolalar asosida:
1. Umumiy sarlavha yarat (aniq, qisqa)
2. Qisqa tavsif yoz (3-5 jumla)
3. Geografik joylashuv

Faqat JSON qaytart:
{"title": "...", "description": "...", "geography": "O'zbekiston"}"""

_semaphore = asyncio.Semaphore(2)


async def _generate_event_info(articles: list[Article]) -> dict:
    """AI yordamida voqea sarlavhasi va tavsifini yaratish."""
    texts = []
    for a in articles[:5]:
        texts.append(f"- {a.title}: {(a.summary or a.content[:200])}")
    combined = "\n".join(texts)

    async with _semaphore:
        for attempt in range(3):
            try:
                import anthropic
                client = anthropic.AsyncAnthropic()
                message = await client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=400,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": combined}],
                )
                raw = message.content[0].text.strip()
                start = raw.find("{")
                end = raw.rfind("}") + 1
                if start >= 0 and end > start:
                    return json.loads(raw[start:end])
            except Exception as e:
                logger.warning(f"Event generation attempt {attempt + 1}: {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)

    return {
        "title": articles[0].title[:200] if articles else "Noma'lum voqea",
        "description": "Bir nechta manba tomonidan xabar berildi.",
        "geography": "O'zbekiston",
    }


def _find_common_entities(articles: list[Article]) -> dict:
    """Maqolalardagi umumiy entitylarni topish."""
    all_companies: list[str] = []
    all_persons: list[str] = []
    all_places: list[str] = []

    for a in articles:
        if a.entities:
            all_companies.extend(a.entities.get("companies", []))
            all_persons.extend(a.entities.get("persons", []))
            all_places.extend(a.entities.get("places", []))

    def most_common(lst: list[str], top: int = 3) -> list[str]:
        from collections import Counter
        return [item for item, _ in Counter(lst).most_common(top)]

    return {
        "companies": most_common(all_companies),
        "persons": most_common(all_persons),
        "places": most_common(all_places),
    }


async def detect_events() -> int:
    """Oxirgi 24 soatdagi maqolalardan voqealar yaratish."""
    since = datetime.utcnow() - timedelta(hours=24)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Article).where(
                and_(
                    Article.created_at >= since,
                    Article.is_processed == True,
                    Article.is_duplicate == False,
                    Article.category != None,
                )
            )
        )
        articles = result.scalars().all()

    if not articles:
        logger.info("No processed articles for event detection")
        return 0

    # Kategoriya bo'yicha guruhlash
    by_category: dict[str, list[Article]] = {}
    for article in articles:
        cat = article.category.value if article.category else "other"
        by_category.setdefault(cat, []).append(article)

    events_created = 0

    for category, cat_articles in by_category.items():
        if len(cat_articles) < 3:
            continue

        # Entity o'xshashligiga qarab guruhlash
        groups = _group_by_entity(cat_articles)

        for group in groups:
            if len(group) < 3:
                continue

            event_info = await _generate_event_info(group)
            entities = _find_common_entities(group)

            async with AsyncSessionLocal() as session:
                event = Event(
                    title=event_info.get("title", group[0].title[:200]),
                    description=event_info.get("description", ""),
                    category=group[0].category or ArticleCategory.economics,
                    impact_level=ImpactLevel.national,
                    source_count=len(group),
                    geography=event_info.get("geography", "O'zbekiston"),
                    entities=entities,
                    timeline=[
                        {"source": a.source_id, "time": str(a.published_at), "title": a.title[:100]}
                        for a in group
                    ],
                    first_seen_at=min(a.published_at for a in group),
                )

                # Score hisoblash
                score, priority = calculate_event_score(event, group)
                event.event_score = score
                event.priority = EventPriority(priority)

                session.add(event)
                await session.flush()

                for idx, article in enumerate(group):
                    from database.models import ArticleRole
                    role = ArticleRole.primary if idx == 0 else ArticleRole.supporting
                    ea = EventArticle(event_id=event.id, article_id=article.id, role=role)
                    session.add(ea)

                await session.commit()
                events_created += 1
                logger.info(f"Created event: {event.title[:60]} (score={score})")

    return events_created


def _group_by_entity(articles: list[Article]) -> list[list[Article]]:
    """Entity o'xshashligiga qarab maqolalarni guruhlash."""
    groups: list[list[Article]] = []
    used = set()

    for i, a in enumerate(articles):
        if i in used:
            continue
        group = [a]
        used.add(i)

        a_entities = set()
        if a.entities:
            a_entities.update(a.entities.get("companies", []))
            a_entities.update(a.entities.get("persons", []))

        for j, b in enumerate(articles):
            if j in used or i == j:
                continue
            b_entities = set()
            if b.entities:
                b_entities.update(b.entities.get("companies", []))
                b_entities.update(b.entities.get("persons", []))

            if a_entities and b_entities and len(a_entities & b_entities) >= 1:
                group.append(b)
                used.add(j)

        groups.append(group)

    return groups
