from datetime import timezone, timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.utils.message_texts import ACCESS_DENIED, PERMISSION_DENIED
from domain.enums import UserRole, UserStatus
from infrastructure.database.connection import AsyncSessionLocal
from infrastructure.repositories.log_repo import AuditLogRepo

_TZ = timezone(timedelta(hours=5))

router = Router()

_ALLOWED_ROLES = {UserRole.SUPERADMIN.value, UserRole.ADMIN.value}


@router.message(Command("logs"))
async def logs_handler(message: Message, db_user=None) -> None:
    if db_user is None:
        await message.answer(ACCESS_DENIED)
        return
    if db_user.status == UserStatus.BLOCKED.value:
        await message.answer(ACCESS_DENIED)
        return
    if db_user.role not in _ALLOWED_ROLES:
        await message.answer(PERMISSION_DENIED)
        return

    async with AsyncSessionLocal() as session:
        repo = AuditLogRepo(session)
        logs = await repo.list_recent(limit=20)

    if not logs:
        await message.answer("Loglar bo'sh.")
        return

    lines = ["<b>OXIRGI LOGLAR</b>\n"]
    for log in logs:
        dt = log.created_at.replace(tzinfo=timezone.utc).astimezone(_TZ).strftime("%Y-%m-%d %H:%M")
        obj = f"{log.object_type}:{log.object_id}" if log.object_type else ""
        lines.append(f"🔹 <code>{dt}</code> | {log.action_type} {obj}")
        if log.details:
            lines.append(f"   ↳ {log.details}")

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n...(qisqartirildi)"

    await message.answer(text, parse_mode="HTML")
