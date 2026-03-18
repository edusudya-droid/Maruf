"""/topics handler — mavzularni o'zgartirish."""
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select
from backend.core.database import AsyncSessionLocal
from database.models import User
from bot.keyboards.inline import topics_keyboard


async def topics_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/topics — mavzularni o'zgartirish."""
    tg_id = update.effective_user.id

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == tg_id))
        user = result.scalar_one_or_none()

    selected = user.topics if user else []
    context.user_data["onboarding_step"] = "topics"
    context.user_data["selected_topics"] = list(selected or [])

    await update.message.reply_text(
        "📌 Qiziqish mavzularingizni tanlang:",
        reply_markup=topics_keyboard(list(selected or [])),
    )
