from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.services.settings_service import get_all_settings, update_setting
from bot.keyboards.admin_menu import settings_keyboard
from bot.utils.message_texts import (
    ACCESS_DENIED,
    PERMISSION_DENIED,
    SETTINGS_INVALID,
    SETTINGS_UPDATED,
)
from domain.enums import UserRole, UserStatus
from infrastructure.database.connection import AsyncSessionLocal

router = Router()

_VIEW_ROLES = {UserRole.SUPERADMIN.value, UserRole.ADMIN.value}
_EDIT_ROLES = {UserRole.SUPERADMIN.value}


class EditSettingState(StatesGroup):
    waiting_for_value = State()


@router.message(Command("settings"))
async def settings_handler(message: Message, db_user=None) -> None:
    if db_user is None:
        await message.answer(ACCESS_DENIED)
        return
    if db_user.status == UserStatus.BLOCKED.value:
        await message.answer(ACCESS_DENIED)
        return
    if db_user.role not in _VIEW_ROLES:
        await message.answer(PERMISSION_DENIED)
        return

    async with AsyncSessionLocal() as session:
        result = await get_all_settings(session)

    settings_data = result.get("data", {})
    text = "<b>Tizim sozlamalari:</b>\n\n"
    for k, v in settings_data.items():
        text += f"• <code>{k}</code>: <b>{v}</b>\n"

    kb = None
    if db_user.role in _EDIT_ROLES:
        kb = settings_keyboard(settings_data)

    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("edit_setting:"))
async def edit_setting_callback(
    callback: CallbackQuery, db_user=None, state: FSMContext = None
) -> None:
    if db_user is None or db_user.role not in _EDIT_ROLES:
        await callback.answer(PERMISSION_DENIED, show_alert=True)
        return

    key = callback.data.split(":", 1)[1]
    if state:
        await state.update_data(editing_setting_key=key)
        await state.set_state(EditSettingState.waiting_for_value)

    await callback.message.answer(
        f"<b>{key}</b> uchun yangi qiymat kiriting:"
        f"\n(Bekor qilish: /cancel)",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(EditSettingState.waiting_for_value)
async def process_setting_value(
    message: Message, state: FSMContext, db_user=None
) -> None:
    if db_user is None or db_user.role not in _EDIT_ROLES:
        await message.answer(PERMISSION_DENIED)
        await state.clear()
        return

    data = await state.get_data()
    key = data.get("editing_setting_key")
    value = message.text.strip()
    await state.clear()

    async with AsyncSessionLocal() as session:
        result = await update_setting(
            key=key,
            value=value,
            session=session,
            updated_by_user_id=db_user.id,
        )

    if not result["success"]:
        await message.answer(f"{SETTINGS_INVALID}\n{result['error']['message']}")
        return

    await message.answer(f"{SETTINGS_UPDATED}\n<code>{key}</code> = <b>{value}</b>", parse_mode="HTML")


@router.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.")
