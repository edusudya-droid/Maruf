from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from bot.keyboards.main_menu import main_menu_keyboard
from bot.utils.message_texts import ACCESS_DENIED, ACCESS_GRANTED, USER_BLOCKED
from domain.enums import UserStatus

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message, db_user=None) -> None:
    if db_user is None:
        await message.answer(ACCESS_DENIED)
        return

    if db_user.status == UserStatus.BLOCKED.value:
        await message.answer(USER_BLOCKED)
        return

    kb = main_menu_keyboard(db_user.role)
    await message.answer(
        f"{ACCESS_GRANTED}\n\nSalom, {db_user.full_name or 'foydalanuvchi'}!",
        reply_markup=kb,
    )


@router.message(Command("menu"))
async def menu_handler(message: Message, db_user=None) -> None:
    if db_user is None:
        await message.answer(ACCESS_DENIED)
        return

    if db_user.status == UserStatus.BLOCKED.value:
        await message.answer(USER_BLOCKED)
        return

    kb = main_menu_keyboard(db_user.role)
    await message.answer("Asosiy menyu:", reply_markup=kb)


@router.message(Command("help"))
async def help_handler(message: Message, db_user=None) -> None:
    if db_user is None:
        await message.answer(ACCESS_DENIED)
        return

    text = (
        "<b>Bot buyruqlari:</b>\n\n"
        "/start — Botni ishga tushirish\n"
        "/menu — Asosiy menyu\n"
        "/posts — So'nggi postlar ro'yxati\n"
        "/analyze — Tanlangan post uchun analiz\n"
        "/report — Oxirgi analiz hisoboti\n"
        "/details — Batafsil hisobot\n"
        "/history — Analiz tarixi\n"
        "/logs — Loglar (Admin+)\n"
        "/settings — Sozlamalar (Admin+)\n"
        "/users — Foydalanuvchilar (Superadmin)\n"
    )
    await message.answer(text, parse_mode="HTML")
