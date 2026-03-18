"""/start handler — ro'yxatdan o'tish."""
from telegram import Update
from telegram.ext import ContextTypes
from loguru import logger
from sqlalchemy import select
from backend.core.database import AsyncSessionLocal
from database.models import User, UserLanguage, UserRole, UserFormat
from bot.keyboards.inline import language_keyboard, role_keyboard, topics_keyboard, format_keyboard, main_menu_keyboard


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Yangi foydalanuvchini qabul qilish yoki mavjudini ko'rsatish."""
    user = update.effective_user
    if not user:
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == user.id)
        )
        db_user = result.scalar_one_or_none()

        if db_user:
            await update.message.reply_text(
                f"Xush kelibsiz, {db_user.first_name}! 👋\n\n"
                "Quyidagi buyruqlardan foydalanishingiz mumkin:",
                reply_markup=main_menu_keyboard(),
            )
            return

    # Yangi foydalanuvchi — til tanlash
    context.user_data["onboarding_step"] = "language"
    context.user_data["tg_user"] = {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name or "Foydalanuvchi",
    }

    await update.message.reply_text(
        "🌐 Tilni tanlang / Выберите язык / Choose language:",
        reply_markup=language_keyboard(),
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inline button callback'larini boshqarish."""
    query = update.callback_query
    await query.answer()
    data = query.data
    step = context.user_data.get("onboarding_step")

    if data.startswith("lang_") and step == "language":
        lang_map = {"lang_uz": "uz", "lang_ru": "ru", "lang_en": "en"}
        context.user_data["language"] = lang_map.get(data, "uz")
        context.user_data["onboarding_step"] = "role"
        await query.edit_message_text(
            "👤 Rolingizni tanlang:", reply_markup=role_keyboard()
        )

    elif data.startswith("role_") and step == "role":
        role = data.replace("role_", "")
        context.user_data["role"] = role
        context.user_data["selected_topics"] = []
        context.user_data["onboarding_step"] = "topics"
        await query.edit_message_text(
            "📌 Qiziqish mavzularingizni tanlang (bir nechta tanlash mumkin):",
            reply_markup=topics_keyboard([]),
        )

    elif data.startswith("topic_") and step == "topics":
        topic = data.replace("topic_", "")
        selected = context.user_data.get("selected_topics", [])
        if topic in selected:
            selected.remove(topic)
        else:
            selected.append(topic)
        context.user_data["selected_topics"] = selected
        await query.edit_message_reply_markup(topics_keyboard(selected))

    elif data == "topics_done" and step == "topics":
        context.user_data["onboarding_step"] = "format"
        await query.edit_message_text(
            "📋 Brifing formatini tanlang:", reply_markup=format_keyboard()
        )

    elif data.startswith("format_") and step == "format":
        fmt = data.replace("format_", "")
        context.user_data["format"] = fmt
        await _complete_registration(query, context)

    elif data == "digest":
        from bot.handlers.digest import send_digest
        await send_digest(query, context)

    elif data == "main_menu":
        await query.edit_message_text(
            "Bosh menyu:", reply_markup=main_menu_keyboard()
        )


async def _complete_registration(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ro'yxatdan o'tishni yakunlash va foydalanuvchini saqlash."""
    tg_user = context.user_data.get("tg_user", {})
    language = context.user_data.get("language", "uz")
    role = context.user_data.get("role", "other")
    topics = context.user_data.get("selected_topics", [])
    fmt = context.user_data.get("format", "standard")

    async with AsyncSessionLocal() as session:
        new_user = User(
            telegram_id=tg_user["id"],
            username=tg_user.get("username"),
            first_name=tg_user.get("first_name", "Foydalanuvchi"),
            language=UserLanguage(language),
            user_role=UserRole(role),
            topics=topics,
            format=UserFormat(fmt),
            interest_weights={t: 0.5 for t in topics},
        )
        session.add(new_user)
        await session.commit()
        logger.info(f"New user registered: {tg_user['id']}")

    await query.edit_message_text(
        "✅ Ro'yxatdan o'tish muvaffaqiyatli yakunlandi!\n\n"
        "Endi har kuni brifinglar olishingiz mumkin. 📰\n"
        "Yordam uchun /help buyrug'ini ishlating.",
        reply_markup=main_menu_keyboard(),
    )
