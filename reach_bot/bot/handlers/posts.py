from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.services.post_service import get_recent_posts
from bot.keyboards.posts_menu import post_action_keyboard, posts_keyboard
from bot.utils.message_texts import (
    ACCESS_DENIED,
    PERMISSION_DENIED,
    POSTS_EMPTY,
    POSTS_LOADING,
    POST_SELECTED,
)
from domain.enums import UserRole, UserStatus
from infrastructure.database.connection import AsyncSessionLocal

router = Router()

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
