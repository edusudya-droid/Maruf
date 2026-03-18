"""AI brifing yaratuvchi — tizimning asosiy chiqish moduli."""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger
from sqlalchemy import select, and_
from backend.core.database import AsyncSessionLocal
from database.models import (
    Event, Brief, BriefType, EventPriority, Article
)
from ai.trend_analyzer import analyze_trends
from ai.hidden_event_detector import detect_hidden_events
from backend.core.config import settings

BRIEF_SYSTEM_PROMPT = """Sen strategik monitoring analitikisan.
Berilgan voqealar ro'yxatini tahlil qilib, qisqa va aniq kunlik brifing yarat.

Talablar:
- Maksimal 12 band
- Maksimal 1500 so'z
- Analitik uslub, shovqinsiz
- Har bir voqea uchun: nima bo'ldi + nima uchun muhim
- Oxirida: Decision Insight (1-2 jumla xulosa)

Chiqish formati: JSON"""

BRIEF_USER_TEMPLATE = """Brifing turi: {brief_type}
Sana: {date}

VOQEALAR:
{events_json}

TREND SIGNALLAR:
{trends_json}

RISK SIGNALLAR:
{risks_json}

EMERGING SIGNALS (tasdiqlanmagan):
{hidden_events_json}

Quyidagi JSON strukturasida brifing yarat:
{{
  "title": "...",
  "brief_type": "{brief_type}",
  "date": "{date}",
  "main_event": {{
    "title": "...",
    "description": "...",
    "significance": "...",
    "sources": []
  }},
  "key_events": [
    {{"title": "...", "description": "...", "category": "...", "sources": []}}
  ],
  "legislation": [{{"title": "...", "description": "...", "sources": []}}],
  "economics": [{{"title": "...", "description": "...", "sources": []}}],
  "international": [{{"title": "...", "description": "...", "sources": []}}],
  "risks": [{{"title": "...", "description": "...", "risk_level": "high|medium"}}],
  "opportunities": [{{"title": "...", "description": "..."}}],
  "emerging_signals": [{{"title": "...", "description": "...", "confidence": "low|medium"}}],
  "decision_insight": "..."
}}"""

_semaphore = asyncio.Semaphore(2)

# Vaqt oraliqlarini aniqlash
BRIEF_TIME_WINDOWS = {
    BriefType.morning: (18, 7),   # kechadan ertalabgacha
    BriefType.midday: (7, 13),    # ertalabdan tushgacha
    BriefType.evening: (13, 19),  # tushdan kechgacha
}


def _get_time_filter(brief_type: BriefType) -> tuple[datetime, datetime]:
    """Brief turi uchun vaqt oralig'ini aniqlash."""
    now = datetime.utcnow()

    if brief_type == BriefType.morning:
        end = now.replace(hour=7, minute=30, second=0, microsecond=0)
        start = end - timedelta(hours=13)
    elif brief_type == BriefType.midday:
        end = now.replace(hour=12, minute=30, second=0, microsecond=0)
        start = end - timedelta(hours=5)
    elif brief_type == BriefType.evening:
        end = now.replace(hour=18, minute=30, second=0, microsecond=0)
        start = end - timedelta(hours=6)
    else:
        start = now - timedelta(hours=24)
        end = now

    return start, end


async def _fetch_events(brief_type: BriefType) -> list[Event]:
    """Brief uchun voqealarni tanlash."""
    start, end = _get_time_filter(brief_type)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Event).where(
                and_(
                    Event.created_at >= start,
                    Event.created_at <= end,
                )
            ).order_by(Event.event_score.desc()).limit(20)
        )
        events = result.scalars().all()

    # Yetarli voqea yo'q bo'lsa, vaqt oralig'ini kengaytirish
    if len(events) < 3:
        extended_start = start - timedelta(hours=4)
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Event).where(
                    and_(
                        Event.created_at >= extended_start,
                        Event.created_at <= end,
                    )
                ).order_by(Event.event_score.desc()).limit(20)
            )
            events = result.scalars().all()

    return events


async def _call_ai(brief_type: BriefType, events: list[Event],
                   trends: list[dict], hidden: list[dict]) -> dict:
    """AI ga brief yaratishni buyurish."""
    # Risklari yuqori voqealar
    risks = [
        {"title": e.title, "description": e.description[:200], "risk_score": e.risk_score}
        for e in events if e.risk_score >= 50
    ]

    prompt = BRIEF_USER_TEMPLATE.format(
        brief_type=brief_type.value,
        date=datetime.utcnow().strftime("%Y-%m-%d"),
        events_json=json.dumps(
            [{"title": e.title, "description": e.description[:300],
              "category": e.category.value, "score": e.event_score,
              "priority": e.priority.value}
             for e in events], ensure_ascii=False),
        trends_json=json.dumps(trends[:5], ensure_ascii=False),
        risks_json=json.dumps(risks[:5], ensure_ascii=False),
        hidden_events_json=json.dumps(hidden[:3], ensure_ascii=False),
    )

    async with _semaphore:
        for attempt in range(3):
            try:
                import anthropic
                client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
                message = await client.messages.create(
                    model=settings.AI_MODEL,
                    max_tokens=2000,
                    system=BRIEF_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = message.content[0].text.strip()
                start_idx = raw.find("{")
                end_idx = raw.rfind("}") + 1
                if start_idx >= 0 and end_idx > start_idx:
                    return json.loads(raw[start_idx:end_idx])
            except Exception as e:
                logger.warning(f"Brief generation attempt {attempt + 1}: {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)

    return {}


def _validate_brief(content: dict) -> bool:
    """Brifing sifatini tekshirish."""
    required = ["title", "main_event", "decision_insight"]
    return all(content.get(k) for k in required)


async def generate_brief(brief_type: BriefType) -> Optional[Brief]:
    """Asosiy brief yaratish funksiyasi."""
    logger.info(f"Generating {brief_type.value} brief...")

    events = await _fetch_events(brief_type)
    trends = await analyze_trends(hours=12)
    hidden = await detect_hidden_events()

    if not events:
        logger.warning(f"No events found for {brief_type.value} brief")

    content = await _call_ai(brief_type, events, trends, hidden)

    if not content or not _validate_brief(content):
        logger.error(f"Brief validation failed for {brief_type.value}")
        # Minimal brief yaratish
        content = {
            "title": f"{brief_type.value.capitalize()} brifing — {datetime.utcnow().strftime('%d.%m.%Y')}",
            "brief_type": brief_type.value,
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "main_event": {"title": "Ma'lumot yig'ilmoqda", "description": "...", "significance": "", "sources": []},
            "key_events": [],
            "legislation": [],
            "economics": [],
            "international": [],
            "risks": [],
            "opportunities": [],
            "emerging_signals": [],
            "decision_insight": "Bugungi brifing ma'lumot yetarli emas sababli to'liq yaratilmadi.",
        }

    async with AsyncSessionLocal() as session:
        brief = Brief(
            brief_type=brief_type,
            title=content.get("title", f"{brief_type.value} brief"),
            content=content,
            raw_events=[e.id for e in events],
        )
        session.add(brief)
        await session.commit()
        await session.refresh(brief)

    logger.info(f"Brief created: id={brief.id}, type={brief_type.value}")
    return brief


def personalize_brief(brief_content: dict, user) -> dict:
    """Foydalanuvchi profiliga qarab brifingni moslashtirish."""
    user_format = getattr(user, "format", "standard")
    user_topics = getattr(user, "topics", []) or []

    if user_format == "quick":
        # Faqat main_event + 3 ta key_events + decision_insight
        return {
            "title": brief_content.get("title"),
            "brief_type": brief_content.get("brief_type"),
            "date": brief_content.get("date"),
            "main_event": brief_content.get("main_event"),
            "key_events": (brief_content.get("key_events") or [])[:3],
            "decision_insight": brief_content.get("decision_insight"),
        }
    elif user_format == "extended":
        return brief_content
    else:  # standard
        result = dict(brief_content)
        result["key_events"] = (brief_content.get("key_events") or [])[:8]
        return result
