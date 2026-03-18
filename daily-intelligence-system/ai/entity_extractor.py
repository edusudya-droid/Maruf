"""Matndan shaxslar, kompaniyalar, joylar ajratish."""
import asyncio
import json
from loguru import logger
from backend.core.config import settings

SYSTEM_PROMPT = """Sen matndan entity (ob'ekt) ajratuvchi AI tizimsan.
Matndan quyidagilarni ajrat:
- companies: kompaniya nomlari
- persons: shaxs ismlari (to'liq ism)
- places: joy nomlari, mamlakatlar, shaharlar
- laws: qonun va me'yoriy hujjat nomlari
- projects: loyiha nomlari

Faqat JSON qaytart:
{"companies": [], "persons": [], "places": [], "laws": [], "projects": []}"""

_semaphore = asyncio.Semaphore(2)


async def extract_entities(text: str) -> dict:
    """Matndan entitylarni AI orqali ajratish."""
    async with _semaphore:
        for attempt in range(3):
            try:
                import anthropic
                client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
                message = await client.messages.create(
                    model=settings.AI_MODEL,
                    max_tokens=500,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": text[:2000]}],
                )
                raw = message.content[0].text.strip()
                start = raw.find("{")
                end = raw.rfind("}") + 1
                if start >= 0 and end > start:
                    return json.loads(raw[start:end])
            except Exception as e:
                logger.warning(f"Entity extraction attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)

        return {"companies": [], "persons": [], "places": [], "laws": [], "projects": []}
