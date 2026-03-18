"""/alerts handler."""
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select
from backend.core.database import AsyncSessionLocal
from database.models import Alert


async def alerts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/alerts — High Priority voqealar tarixi."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Alert).order_by(Alert.created_at.desc()).limit(10)
        )
        alerts = result.scalars().all()

    if not alerts:
        await update.message.reply_text("🔕 Hozircha muhim ogohlantirishlar yo'q.")
        return

    text = "🔔 <b>Oxirgi ogohlantirishlar:</b>\n\n"
    for a in alerts:
        icon = "🚨" if a.alert_type.value == "urgent" else "⚠️"
        dt = a.created_at.strftime("%d.%m %H:%M")
        text += f"{icon} <b>{dt}</b>\n{a.title}\n\n"

    await update.message.reply_text(text, parse_mode="HTML")
