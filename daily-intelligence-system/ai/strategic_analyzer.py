"""Strategik tahlil — zaif signallar va kelajak risklari."""
import asyncio
import json
from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy import select, and_
from backend.core.database import AsyncSessionLocal
from database.models import Article, Event

SYSTEM_PROMPT = """Sen strategik tahlilchisan.
Berilgan voqealar va signallar asosida:
1. Zaif signallar — hali keng e'tibor tortmagan, lekin muhim bo'lishi mumkin bo'lgan mavzular
2. Risklar — iqtisodiy, regulyator, siyosiy, tarmoq risklari
3. Imkoniyatlar — yangi biznes yoki investitsiya imkoniyatlari
4. Strategic Risk Index (0-100)

JSON qaytart:
{
  "weak_signals": [{"topic": "...", "description": "...", "probability": "low|medium|high"}],
  "risks": [{"title": "...", "type": "economic|regulatory|political|sector", "level": "low|medium|high"}],
  "opportunities": [{"title": "...", "description": "..."}],
  "strategic_risk_index": 0,
  "summary": "..."
}"""

_semaphore = asyncio.Semaphore(2)


async def analyze_strategy(hours: int = 24) -> dict:
    """Strategik tahlil — so'nggi N soatdagi voqealar asosida."""
    since = datetime.utcnow() - timedelta(hours=hours)

    async with AsyncSessionLocal() as session:
        events_result = await session.execute(
            select(Event).where(Event.created_at >= since)
        )
        events = events_result.scalars().all()

    if not events:
        return {
            "weak_signals": [], "risks": [], "opportunities": [],
            "strategic_risk_index": 0, "summary": "Ma'lumot yetarli emas.",
        }

    events_text = "\n".join([
        f"- [{e.category.value}] {e.title}: {e.description[:200]}"
        for e in events[:20]
    ])

    async with _semaphore:
        for attempt in range(3):
            try:
                import anthropic
                client = anthropic.AsyncAnthropic()
                message = await client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=800,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": events_text}],
                )
                raw = message.content[0].text.strip()
                start = raw.find("{")
                end = raw.rfind("}") + 1
                if start >= 0 and end > start:
                    return json.loads(raw[start:end])
            except Exception as e:
                logger.warning(f"Strategic analysis attempt {attempt + 1}: {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)

    return {
        "weak_signals": [], "risks": [], "opportunities": [],
        "strategic_risk_index": 0, "summary": "Tahlil amalga oshmadi.",
    }
