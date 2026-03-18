"""Maqolani kategoriya va tonallik bo'yicha tasniflash."""
import asyncio
import json
from typing import Optional
import anthropic
from loguru import logger
from backend.core.config import settings

SYSTEM_PROMPT = """Sen O'zbekiston uchun media tahlil qiluvchi AI analitiksan.
Berilgan maqolaga:
1. category — qaysi soha (economics/law/business/international/risk/technology/agriculture/infrastructure)
2. sentiment — kayfiyat (positive/neutral/negative)
3. importance_score — ahamiyat 0.0 dan 1.0 gacha

Faqat JSON qaytart: {"category": "...", "sentiment": "...", "importance_score": 0.0}"""

_semaphore = asyncio.Semaphore(2)


async def classify_article(title: str, content: str) -> dict:
    """Maqolani AI orqali tasniflash."""
    async with _semaphore:
        for attempt in range(3):
            try:
                client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
                text = f"Sarlavha: {title}\n\nMatn: {content[:1500]}"
                message = await client.messages.create(
                    model=settings.AI_MODEL,
                    max_tokens=200,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": text}],
                )
                raw = message.content[0].text.strip()
                # JSON ichidan ajratib olish
                start = raw.find("{")
                end = raw.rfind("}") + 1
                if start >= 0 and end > start:
                    return json.loads(raw[start:end])
            except Exception as e:
                logger.warning(f"Classify attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)

        return {"category": "economics", "sentiment": "neutral", "importance_score": 0.3}
