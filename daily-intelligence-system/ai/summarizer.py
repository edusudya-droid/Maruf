"""Maqolani 2-3 jumlada qisqartirish."""
import asyncio
from loguru import logger
from backend.core.config import settings

SYSTEM_PROMPT = """Sen professional media xulosa qiluvchisan.
Berilgan maqolani 2-3 jumlada qisqacha yoz.
Faqat eng muhim ma'lumotlarni qoldir.
Til: maqola tilidagi.
Hech qanday qo'shimcha tushuntirish yozma, faqat xulosa."""

_semaphore = asyncio.Semaphore(2)


async def summarize_article(title: str, content: str, language: str = "uz") -> str:
    """Maqolani qisqartirish."""
    async with _semaphore:
        for attempt in range(3):
            try:
                import anthropic
                client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
                text = f"Sarlavha: {title}\n\nMatn: {content[:2000]}"
                message = await client.messages.create(
                    model=settings.AI_MODEL,
                    max_tokens=300,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": text}],
                )
                return message.content[0].text.strip()
            except Exception as e:
                logger.warning(f"Summarize attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)

        # Fallback: dastlabki 200 belgi
        return content[:200] + "..."
