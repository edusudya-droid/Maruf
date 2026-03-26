from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from bot.utils.message_texts import ACCESS_DENIED, USER_BLOCKED
from infrastructure.database.connection import AsyncSessionLocal
from infrastructure.repositories.user_repo import UserRepo


class AuthMiddleware(BaseMiddleware):
    """
    Attach user ORM object (or None) to handler data.
    Handlers then call check_user_access from auth_service for fine-grained checks.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        telegram_user = data.get("event_from_user")
        db_user = None

        if telegram_user:
            async with AsyncSessionLocal() as session:
                repo = UserRepo(session)
                db_user = await repo.get_by_telegram_id(telegram_user.id)

        data["db_user"] = db_user
        return await handler(event, data)
