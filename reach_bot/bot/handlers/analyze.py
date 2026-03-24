from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.services.analysis_service import start_analysis
from bot.utils.message_texts import (
    ACCESS_DENIED,
    ANALYZE_ALREADY_RUNNING,
    ANALYZE_DAILY_LIMIT,
    ANALYZE_NO_POST,
    ANALYZE_STARTED,
    ERROR_OCCURRED,
    PERMISSION_DENIED,
)
from domain.enums import UserRole, UserStatus
from infrastructure.database.connection import AsyncSessionLocal

router = Router()

_ALLOWED_ROLES = {UserRole.SUPERADMIN.value, UserRole.ADMIN.value, UserRole.ANALYST.value}


@router.message(Command("analyze"))
async def analyze_handler(message: Message, db_user=None, state: FSMContext = None) -> None:
    if db_user is None:
        await message.answer(ACCESS_DENIED)
        return

    if db_user.status == UserStatus.BLOCKED.value:
        await message.answer(ACCESS_DENIED)
        return

    if db_user.role not in _ALLOWED_ROLES:
        await message.answer(PERMISSION_DENIED)
        return

    post_id = None
    if state:
        data = await state.get_data()
        post_id = data.get("selected_post_id")

    if not post_id:
        await message.answer(ANALYZE_NO_POST)
        return

    await _do_analyze(message, db_user.id, post_id)


@router.callback_query(F.data.startswith("start_analyze:"))
async def start_analyze_callback(
    callback: CallbackQuery, db_user=None, state: FSMContext = None
) -> None:
    if db_user is None or db_user.role not in _ALLOWED_ROLES:
        await callback.answer(PERMISSION_DENIED, show_alert=True)
        return

    post_id = int(callback.data.split(":")[1])

    if state:
        await state.update_data(selected_post_id=post_id)

    await callback.message.answer("Analiz ishga tushirilmoqda...")
    await callback.answer()
    await _do_analyze(callback.message, db_user.id, post_id)


async def _do_analyze(message: Message, user_db_id: int, post_id: int) -> None:
    async with AsyncSessionLocal() as session:
        result = await start_analysis(
            source_post_id=post_id,
            user_id=user_db_id,
            session=session,
        )

    if not result["success"]:
        code = result["error"]["code"]
        if code == "ANALYSIS_ALREADY_RUNNING":
            await message.answer(ANALYZE_ALREADY_RUNNING)
        elif code == "DAILY_LIMIT_REACHED":
            await message.answer(ANALYZE_DAILY_LIMIT)
        elif code == "POST_NOT_FOUND":
            await message.answer(ANALYZE_NO_POST)
        else:
            await message.answer(f"{ERROR_OCCURRED}\n{result['error']['message']}")
        return

    run_id = result["data"]["analysis_run_id"]
    await message.answer(
        f"{ANALYZE_STARTED}\n\n"
        f"Analiz ID: <code>{run_id}</code>\n"
        f"Natija tayyor bo'lganda /report buyrug'i bilan ko'ring.",
        parse_mode="HTML",
    )
