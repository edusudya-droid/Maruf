from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.services.report_service import list_history
from bot.utils.message_texts import ACCESS_DENIED
from domain.enums import UserStatus
from infrastructure.database.connection import AsyncSessionLocal

router = Router()


@router.message(Command("history"))
async def history_handler(message: Message, db_user=None) -> None:
    if db_user is None:
        await message.answer(ACCESS_DENIED)
        return

    if db_user.status == UserStatus.BLOCKED.value:
        await message.answer(ACCESS_DENIED)
        return

    async with AsyncSessionLocal() as session:
        result = await list_history(session, limit=20)

    if not result["success"]:
        await message.answer("Tarixni olishda xato yuz berdi.")
        return

    runs = result["data"]
    if not runs:
        await message.answer("Hali hech qanday analiz bajarilmagan.")
        return

    lines = ["<b>ANALIZ TARIXI</b>\n"]
    for run in runs:
        started = run["started_at"][:19].replace("T", " ")
        status_icon = {
            "COMPLETED": "✅",
            "COMPLETED_WITH_SKIPS": "⚠️",
            "FAILED": "❌",
            "RUNNING": "🔄",
            "PENDING": "⏳",
        }.get(run["status"], "❓")
        lines.append(
            f"{status_icon} ID:{run['id']} | {started}\n"
            f"   Qamrov: {run['total_confirmed_reach']:,} | {run['post_url']}\n"
        )

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n...(qisqartirildi)"

    await message.answer(text, parse_mode="HTML")
