import logging
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import BaseFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, MessageOriginChannel


class IsForwardedFromChannel(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        # Bot API 7.0+ (yangi format)
        if isinstance(getattr(message, "forward_origin", None), MessageOriginChannel):
            return True
        # Eski format (forward restriction bo'lgan kanallar)
        if getattr(message, "forward_from_chat", None) is not None:
            return True
        return False

from app.services.post_service import get_recent_posts
from bot.keyboards.posts_menu import post_action_keyboard, posts_keyboard
from bot.utils.message_texts import (
    ACCESS_DENIED,
    PERMISSION_DENIED,
    POSTS_EMPTY,
    POSTS_LOADING,
    POST_SELECTED,
)
from config import settings as app_settings
from domain.enums import UserRole, UserStatus
from infrastructure.database.connection import AsyncSessionLocal
from infrastructure.repositories.post_repo import PostRepo

router = Router()
logger = logging.getLogger(__name__)

_ALLOWED_ROLES = {UserRole.SUPERADMIN.value, UserRole.ADMIN.value, UserRole.ANALYST.value}


@router.message(Command("posts"))
async def posts_handler(message: Message, db_user=None, state: FSMContext = None) -> None:
    if db_user is None:
        await message.answer(ACCESS_DENIED)
        return

    if db_user.status == UserStatus.BLOCKED.value:
        await message.answer(ACCESS_DENIED)
        return

    if db_user.role not in _ALLOWED_ROLES:
        await message.answer(PERMISSION_DENIED)
        return

    loading = await message.answer(POSTS_LOADING)

    async with AsyncSessionLocal() as session:
        result = await get_recent_posts(session)

    if not result["success"]:
        await loading.edit_text(f"Xato: {result['error']['message']}")
        return

    posts = result["data"]
    if not posts:
        await loading.edit_text(POSTS_EMPTY)
        return

    kb = posts_keyboard(posts)
    await loading.edit_text(
        f"So'nggi <b>{len(posts)}</b> ta post:", reply_markup=kb, parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("select_post:"))
async def select_post_callback(callback: CallbackQuery, db_user=None, state: FSMContext = None) -> None:
    if db_user is None or db_user.role not in _ALLOWED_ROLES:
        await callback.answer(PERMISSION_DENIED, show_alert=True)
        return

    post_id = int(callback.data.split(":")[1])

    # Store selected post in FSM state
    if state:
        await state.update_data(selected_post_id=post_id)

    kb = post_action_keyboard(post_id)
    await callback.message.edit_text(
        f"Post tanlandi (ID: {post_id}).\n{POST_SELECTED}",
        reply_markup=kb,
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_posts")
async def back_to_posts_callback(callback: CallbackQuery, db_user=None) -> None:
    if db_user is None or db_user.role not in _ALLOWED_ROLES:
        await callback.answer(PERMISSION_DENIED, show_alert=True)
        return

    async with AsyncSessionLocal() as session:
        result = await get_recent_posts(session)

    posts = result.get("data", [])
    if not posts:
        await callback.message.edit_text(POSTS_EMPTY)
        return

    kb = posts_keyboard(posts)
    await callback.message.edit_text(
        f"So'nggi <b>{len(posts)}</b> ta post:", reply_markup=kb, parse_mode="HTML"
    )
    await callback.answer()


@router.message(IsForwardedFromChannel())
async def forwarded_post_handler(message: Message, db_user=None) -> None:
    """Admin kanaldan post forward qilsa — bazaga saqlaydi."""
    logger.info("forwarded_post_handler chaqirildi, db_user=%s", db_user)
    if db_user is None:
        await message.answer("[DEBUG] db_user topilmadi.")
        return
    if db_user.role not in _ALLOWED_ROLES:
        await message.answer(f"[DEBUG] Ruxsat yo'q. Rolingiz: {db_user.role}")
        return

    try:
        # Bot API 7.0+ (yangi format)
        origin = getattr(message, "forward_origin", None)
        # Eski format (restricted channel)
        forward_chat = getattr(message, "forward_from_chat", None)

        if origin is not None and isinstance(origin, MessageOriginChannel):
            channel_id = origin.chat.id
            msg_id = origin.message_id
            channel_title = origin.chat.title or "Official Channel"
            published_at = (
                origin.date if isinstance(origin.date, datetime)
                else datetime.fromtimestamp(origin.date, tz=timezone.utc)
            )
        elif forward_chat is not None:
            channel_id = forward_chat.id
            msg_id = getattr(message, "forward_from_message_id", None) or message.message_id
            channel_title = forward_chat.title or "Official Channel"
            fwd_date = getattr(message, "forward_date", None)
            published_at = (
                fwd_date if isinstance(fwd_date, datetime)
                else datetime.fromtimestamp(fwd_date, tz=timezone.utc)
            ) if fwd_date else datetime.now(timezone.utc)
        else:
            await message.answer("[DEBUG] Forward ma'lumoti topilmadi.")
            return

        if channel_id != app_settings.official_channel_id:
            await message.answer(
                f"Bu post rasmiy kanaldan emas.\n"
                f"Kelgan chat_id: <code>{channel_id}</code>\n"
                f"Kutilgan: <code>{app_settings.official_channel_id}</code>"
            )
            return

        post_url = f"{app_settings.official_channel_url}/{msg_id}"
        post_text = message.text or message.caption

        async with AsyncSessionLocal() as session:
            repo = PostRepo(session)
            channel = await repo.get_or_create_channel(
                telegram_channel_id=channel_id,
                channel_title=channel_title,
                channel_url=app_settings.official_channel_url,
            )
            await repo.upsert(
                official_channel_id=channel.id,
                telegram_message_id=msg_id,
                post_url=post_url,
                post_text=post_text,
                published_at=published_at,
                views_count=None,
                collected_at=datetime.now(timezone.utc),
            )
            await session.commit()

        logger.info("Forward orqali post saqlandi: message_id=%s", msg_id)
        await message.answer(f"Post saqlandi (message_id={msg_id})")

    except Exception as exc:
        logger.exception("Forward post saqlashda xato: %s", exc)
        await message.answer(f"Xato yuz berdi: {exc}")
