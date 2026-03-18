"""/digest handler — so'nggi brifingni ko'rsatish."""
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select
from backend.core.database import AsyncSessionLocal
from database.models import Brief, User
from ai.brief_generator import personalize_brief
from notifications.telegram_sender import format_brief_message
from bot.keyboards.inline import back_keyboard


async def digest_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/digest komandasi."""
    await _send_latest_brief(update.message, update.effective_user.id, context)


async def send_digest(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inline button orqali so'nggi digest yuborish."""
    user_id = query.from_user.id
    await _send_latest_brief(query.message, user_id, context, edit=True)


async def _send_latest_brief(message, tg_id: int, context, edit: bool = False) -> None:
    """Eng so'nggi brifingni topib, foydalanuvchiga yuborish."""
    async with AsyncSessionLocal() as session:
        # Foydalanuvchini topish
        user_result = await session.execute(
            select(User).where(User.telegram_id == tg_id)
        )
        user = user_result.scalar_one_or_none()

        # Eng so'nggi brief
        brief_result = await session.execute(
            select(Brief).order_by(Brief.created_at.desc()).limit(1)
        )
        brief = brief_result.scalar_one_or_none()

    if not brief:
        text = "📭 Hozircha brifing mavjud emas. Keyinroq qayta urinib ko'ring."
        if edit:
            await message.edit_text(text, reply_markup=back_keyboard())
        else:
            await message.reply_text(text)
        return

    content = brief.content
    if user:
        content = personalize_brief(content, user)

    text = format_brief_message(content)

    if edit:
        await message.edit_text(
            text, parse_mode="HTML", reply_markup=back_keyboard()
        )
    else:
        await message.reply_text(text, parse_mode="HTML")
