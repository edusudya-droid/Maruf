from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.services.user_service import (
    add_user,
    change_role,
    list_users,
    set_user_status,
)
from bot.keyboards.admin_menu import roles_keyboard, user_actions_keyboard, users_list_keyboard
from bot.utils.message_texts import (
    ACCESS_DENIED,
    PERMISSION_DENIED,
    USER_ADDED,
    USER_ALREADY_EXISTS,
    USER_BLOCKED_MSG,
    USER_NOT_FOUND,
    USER_ROLE_CHANGED,
    USER_UNBLOCKED_MSG,
)
from domain.enums import UserRole, UserStatus
from infrastructure.database.connection import AsyncSessionLocal

router = Router()


class AddUserState(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_role = State()


@router.message(Command("users"))
async def users_handler(message: Message, db_user=None) -> None:
    if db_user is None:
        await message.answer(ACCESS_DENIED)
        return
    if db_user.role != UserRole.SUPERADMIN.value:
        await message.answer(PERMISSION_DENIED)
        return

    async with AsyncSessionLocal() as session:
        result = await list_users(session)

    users = result.get("data", [])
    if not users:
        await message.answer("Hali foydalanuvchilar yo'q.")
        return

    kb = users_list_keyboard(users)
    await message.answer(
        f"<b>Foydalanuvchilar ({len(users)} ta):</b>",
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.message(Command("adduser"))
async def adduser_handler(message: Message, db_user=None, state: FSMContext = None) -> None:
    if db_user is None:
        await message.answer(ACCESS_DENIED)
        return
    if db_user.role != UserRole.SUPERADMIN.value:
        await message.answer(PERMISSION_DENIED)
        return

    await message.answer(
        "Yangi foydalanuvchining Telegram ID sini kiriting:"
    )
    if state:
        await state.set_state(AddUserState.waiting_for_user_id)


@router.message(AddUserState.waiting_for_user_id)
async def process_user_id(message: Message, state: FSMContext, db_user=None) -> None:
    if db_user is None or db_user.role != UserRole.SUPERADMIN.value:
        await message.answer(PERMISSION_DENIED)
        await state.clear()
        return

    try:
        tg_id = int(message.text.strip())
    except ValueError:
        await message.answer("Noto'g'ri format. Raqam kiriting:")
        return

    await state.update_data(new_user_telegram_id=tg_id)
    await state.set_state(AddUserState.waiting_for_role)
    await message.answer(
        "Rolni tanlang:\n"
        "SUPERADMIN | ADMIN | ANALYST | VIEWER"
    )


@router.message(AddUserState.waiting_for_role)
async def process_role(message: Message, state: FSMContext, db_user=None) -> None:
    if db_user is None or db_user.role != UserRole.SUPERADMIN.value:
        await message.answer(PERMISSION_DENIED)
        await state.clear()
        return

    role = message.text.strip().upper()
    valid_roles = [r.value for r in UserRole]
    if role not in valid_roles:
        await message.answer(f"Noto'g'ri rol. Quyidagilardan birini kiriting: {', '.join(valid_roles)}")
        return

    data = await state.get_data()
    tg_id = data.get("new_user_telegram_id")
    await state.clear()

    async with AsyncSessionLocal() as session:
        result = await add_user(
            telegram_user_id=tg_id,
            role=role,
            full_name=None,
            username=None,
            session=session,
            performed_by_user_id=db_user.id,
        )

    if not result["success"]:
        code = result["error"]["code"]
        if code == "USER_ALREADY_EXISTS":
            await message.answer(USER_ALREADY_EXISTS)
        else:
            await message.answer(f"Xato: {result['error']['message']}")
        return

    await message.answer(f"{USER_ADDED}\nTelegram ID: {tg_id} | Rol: {role}")


@router.callback_query(F.data.startswith("user_detail:"))
async def user_detail_callback(callback: CallbackQuery, db_user=None) -> None:
    if db_user is None or db_user.role != UserRole.SUPERADMIN.value:
        await callback.answer(PERMISSION_DENIED, show_alert=True)
        return

    user_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        result = await list_users(session)

    user = next((u for u in result.get("data", []) if u["id"] == user_id), None)
    if not user:
        await callback.answer(USER_NOT_FOUND, show_alert=True)
        return

    name = user.get("full_name") or user.get("username") or str(user["telegram_user_id"])
    kb = user_actions_keyboard(user_id, user["status"])
    await callback.message.edit_text(
        f"👤 <b>{name}</b>\n"
        f"Rol: {user['role']}\n"
        f"Status: {user['status']}\n"
        f"TG ID: {user['telegram_user_id']}",
        reply_markup=kb,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("block_user:"))
async def block_user_callback(callback: CallbackQuery, db_user=None) -> None:
    if db_user is None or db_user.role != UserRole.SUPERADMIN.value:
        await callback.answer(PERMISSION_DENIED, show_alert=True)
        return

    user_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        result = await set_user_status(
            target_user_id=user_id,
            status="BLOCKED",
            session=session,
            performed_by_user_id=db_user.id,
        )

    if result["success"]:
        await callback.answer(USER_BLOCKED_MSG)
    else:
        await callback.answer(result["error"]["message"], show_alert=True)


@router.callback_query(F.data.startswith("unblock_user:"))
async def unblock_user_callback(callback: CallbackQuery, db_user=None) -> None:
    if db_user is None or db_user.role != UserRole.SUPERADMIN.value:
        await callback.answer(PERMISSION_DENIED, show_alert=True)
        return

    user_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        result = await set_user_status(
            target_user_id=user_id,
            status="ACTIVE",
            session=session,
            performed_by_user_id=db_user.id,
        )

    if result["success"]:
        await callback.answer(USER_UNBLOCKED_MSG)
    else:
        await callback.answer(result["error"]["message"], show_alert=True)


@router.callback_query(F.data.startswith("change_role:"))
async def change_role_callback(callback: CallbackQuery, db_user=None) -> None:
    if db_user is None or db_user.role != UserRole.SUPERADMIN.value:
        await callback.answer(PERMISSION_DENIED, show_alert=True)
        return

    user_id = int(callback.data.split(":")[1])
    kb = roles_keyboard(user_id)
    await callback.message.edit_text("Yangi rolni tanlang:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("set_role:"))
async def set_role_callback(callback: CallbackQuery, db_user=None) -> None:
    if db_user is None or db_user.role != UserRole.SUPERADMIN.value:
        await callback.answer(PERMISSION_DENIED, show_alert=True)
        return

    _, user_id_str, new_role = callback.data.split(":")
    user_id = int(user_id_str)

    async with AsyncSessionLocal() as session:
        result = await change_role(
            target_user_id=user_id,
            new_role=new_role,
            session=session,
            performed_by_user_id=db_user.id,
        )

    if result["success"]:
        await callback.answer(USER_ROLE_CHANGED)
    else:
        await callback.answer(result["error"]["message"], show_alert=True)


@router.callback_query(F.data == "back_to_users")
async def back_to_users_callback(callback: CallbackQuery, db_user=None) -> None:
    if db_user is None or db_user.role != UserRole.SUPERADMIN.value:
        await callback.answer(PERMISSION_DENIED, show_alert=True)
        return

    async with AsyncSessionLocal() as session:
        result = await list_users(session)

    users = result.get("data", [])
    kb = users_list_keyboard(users)
    await callback.message.edit_text(
        f"<b>Foydalanuvchilar ({len(users)} ta):</b>",
        reply_markup=kb,
        parse_mode="HTML",
    )
    await callback.answer()
