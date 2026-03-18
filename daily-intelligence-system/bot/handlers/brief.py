"""/brief [mavzu] handler — tematik brief."""
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select
from backend.core.database import AsyncSessionLocal
from database.models import Brief, BriefType, User
from ai.brief_generator import generate_brief, personalize_brief
from notifications.telegram_sender import format_brief_message


async def brief_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/brief [mavzu] — berilgan mavzu bo'yicha brief."""
    args = context.args
    if not args:
        await update.message.reply_text(
            "Foydalanish: /brief [mavzu]\n\nMasalan: /brief iqtisodiyot"
        )
        return

    topic = " ".join(args).lower()
    await update.message.reply_text(f"⏳ '{topic}' mavzusi bo'yicha brief yaratilmoqda...")

    brief = await generate_brief(BriefType.thematic)

    async with AsyncSessionLocal() as session:
        user_result = await session.execute(
            select(User).where(User.telegram_id == update.effective_user.id)
        )
        user = user_result.scalar_one_or_none()

    content = brief.content if brief else {}
    if user and content:
        content = personalize_brief(content, user)

    text = format_brief_message(content) if content else "Brief yaratib bo'lmadi."
    await update.message.reply_text(text, parse_mode="HTML")
