"""/archive handler."""
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import select, and_
from backend.core.database import AsyncSessionLocal
from database.models import Brief


async def archive_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/archive — arxiv menyusi."""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Kecha", callback_data="archive_yesterday")],
        [InlineKeyboardButton("📆 Hafta davomida", callback_data="archive_week")],
        [InlineKeyboardButton("🗓️ Oy davomida", callback_data="archive_month")],
    ])
    await update.message.reply_text("📁 Arxiv:", reply_markup=keyboard)


async def archive_callback(query, period: str) -> None:
    """Arxiv so'rovini boshqarish."""
    now = datetime.utcnow()

    if period == "yesterday":
        start = now - timedelta(days=1)
        label = "Kecha"
    elif period == "week":
        start = now - timedelta(days=7)
        label = "Oxirgi 7 kun"
    else:
        start = now - timedelta(days=30)
        label = "Oxirgi 30 kun"

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Brief)
            .where(Brief.created_at >= start)
            .order_by(Brief.created_at.desc())
            .limit(10)
        )
        briefs = result.scalars().all()

    if not briefs:
        await query.edit_message_text(f"📭 {label} uchun brifing topilmadi.")
        return

    text = f"📁 <b>{label} brifinglar:</b>\n\n"
    for b in briefs:
        dt = b.created_at.strftime("%d.%m %H:%M")
        text += f"• {dt} — {b.brief_type.value}: {b.title[:60]}\n"

    await query.edit_message_text(text, parse_mode="HTML")
