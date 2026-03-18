"""/settings handler — sozlamalar."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import select
from backend.core.database import AsyncSessionLocal
from database.models import User, UserFormat
from bot.keyboards.inline import format_keyboard, language_keyboard


async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/settings — foydalanuvchi sozlamalari."""
    tg_id = update.effective_user.id

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == tg_id))
        user = result.scalar_one_or_none()

    if not user:
        await update.message.reply_text("Avval /start buyrug'ini ishlating.")
        return

    text = (
        f"⚙️ <b>Sozlamalar</b>\n\n"
        f"👤 Ism: {user.first_name}\n"
        f"🌐 Til: {user.language.value}\n"
        f"💼 Rol: {user.user_role.value}\n"
        f"📋 Format: {user.format.value}\n"
        f"🕐 Vaqt: {user.send_time}\n"
        f"📌 Mavzular: {', '.join(user.topics or []) or 'belgilanmagan'}"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Formatni o'zgartirish", callback_data="change_format")],
        [InlineKeyboardButton("🌐 Tilni o'zgartirish", callback_data="change_lang")],
        [InlineKeyboardButton("🕐 Vaqtni o'zgartirish", callback_data="change_time")],
    ])

    await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)
