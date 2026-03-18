"""Telegram orqali brifinglarni yuborish."""
import asyncio
from typing import Optional
from loguru import logger
from telegram import Bot
from telegram.constants import ParseMode
from sqlalchemy import select
from backend.core.config import settings
from backend.core.database import AsyncSessionLocal
from database.models import User, Brief


def format_brief_message(content: dict) -> str:
    """Brief content dict'ini Telegram HTML formatiga o'tkazish."""
    if not content:
        return "📭 Brifing mavjud emas."

    parts = []

    title = content.get("title", "Kunlik Brifing")
    date = content.get("date", "")
    parts.append(f"📊 <b>{title}</b>\n{date}\n")

    # Asosiy voqea
    main = content.get("main_event")
    if main and main.get("title"):
        parts.append(
            f"🔥 <b>ASOSIY VOQEA</b>\n"
            f"<b>{main['title']}</b>\n"
            f"{main.get('description', '')}\n"
            f"<i>{main.get('significance', '')}</i>"
        )

    # Muhim voqealar
    key_events = content.get("key_events", [])
    if key_events:
        parts.append("📌 <b>MUHIM VOQEALAR</b>")
        for ev in key_events[:5]:
            parts.append(f"• <b>{ev['title']}</b>\n  {ev.get('description', '')[:150]}")

    # Qonunchilik
    legislation = content.get("legislation", [])
    if legislation:
        parts.append("⚖️ <b>QONUNCHILIK</b>")
        for item in legislation[:3]:
            parts.append(f"• {item['title']}: {item.get('description', '')[:100]}")

    # Iqtisodiyot
    economics = content.get("economics", [])
    if economics:
        parts.append("💹 <b>IQTISODIYOT</b>")
        for item in economics[:3]:
            parts.append(f"• {item['title']}: {item.get('description', '')[:100]}")

    # Xalqaro
    international = content.get("international", [])
    if international:
        parts.append("🌍 <b>XALQARO</b>")
        for item in international[:2]:
            parts.append(f"• {item['title']}")

    # Risklar
    risks = content.get("risks", [])
    if risks:
        parts.append("⚠️ <b>RISKLAR</b>")
        for r in risks[:3]:
            level_icon = "🔴" if r.get("risk_level") == "high" else "🟡"
            parts.append(f"{level_icon} {r['title']}: {r.get('description', '')[:100]}")

    # Imkoniyatlar
    opportunities = content.get("opportunities", [])
    if opportunities:
        parts.append("✅ <b>IMKONIYATLAR</b>")
        for op in opportunities[:2]:
            parts.append(f"• {op['title']}")

    # Emerging signals
    signals = content.get("emerging_signals", [])
    if signals:
        parts.append("🔍 <b>EMERGING SIGNALS</b>")
        for sig in signals[:2]:
            conf = sig.get("confidence", "low")
            parts.append(f"〽️ [{conf.upper()}] {sig['title']}")

    # Decision Insight
    insight = content.get("decision_insight")
    if insight:
        parts.append(f"\n💡 <b>DECISION INSIGHT</b>\n<i>{insight}</i>")

    return "\n\n".join(parts)


async def send_brief_to_all_users(brief: Brief) -> int:
    """Barcha faol foydalanuvchilarga brief yuborish."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.is_active == True)
        )
        users = result.scalars().all()

    if not users:
        logger.warning("No active users to send brief")
        return 0

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    from ai.brief_generator import personalize_brief

    sent_count = 0
    for user in users:
        try:
            content = personalize_brief(brief.content, user)
            text = format_brief_message(content)

            # Telegram maksimum 4096 belgi
            if len(text) > 4000:
                text = text[:3997] + "..."

            await bot.send_message(
                chat_id=user.telegram_id,
                text=text,
                parse_mode=ParseMode.HTML,
            )
            sent_count += 1
            await asyncio.sleep(0.05)  # Rate limit

        except Exception as e:
            logger.warning(f"Failed to send to user {user.telegram_id}: {e}")

    # brief.sent_at va recipient_count yangilash
    async with AsyncSessionLocal() as session:
        from datetime import datetime
        result = await session.get(Brief, brief.id)
        if result:
            result.sent_at = datetime.utcnow()
            result.recipient_count = sent_count
            await session.commit()

    logger.info(f"Brief sent to {sent_count}/{len(users)} users")
    return sent_count
