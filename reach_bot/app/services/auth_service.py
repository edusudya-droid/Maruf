from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import UserRole, UserStatus
from domain.exceptions import (
    AuthDeniedError,
    UserBlockedError,
    ok,
    err,
)
from infrastructure.database.models import User
from infrastructure.repositories.user_repo import UserRepo


# Permissions matrix: role -> set of allowed features
_PERMISSIONS: dict[UserRole, set[str]] = {
    UserRole.SUPERADMIN: {
        "start", "posts", "analyze", "report", "details",
        "history", "logs", "settings_view", "settings_edit", "users",
    },
    UserRole.ADMIN: {
        "start", "posts", "analyze", "report", "details",
        "history", "logs", "settings_view", "settings_edit_partial",
    },
    UserRole.ANALYST: {
        "start", "posts", "analyze", "report", "details", "history",
    },
    UserRole.VIEWER: {
        "start", "report", "details", "history",
    },
}


async def check_user_access(
    telegram_user_id: int,
    session: AsyncSession,
    required_permission: Optional[str] = None,
) -> dict:
    """
    Verify that the telegram user exists, is ACTIVE, and (optionally) has the
    required permission.

    Returns standard {success, data, error, meta} dict.
    data = User ORM object on success.
    """
    repo = UserRepo(session)
    user: Optional[User] = await repo.get_by_telegram_id(telegram_user_id)

    if user is None:
        return err(AuthDeniedError("Tizimda ro'yxatdan o'tmagan foydalanuvchi"))

    if user.status == UserStatus.BLOCKED:
        return err(UserBlockedError())

    if required_permission:
        role = UserRole(user.role)
        allowed = _PERMISSIONS.get(role, set())
        if required_permission not in allowed:
            from domain.exceptions import PermissionDeniedError
            return err(PermissionDeniedError())

    return ok(data=user)


def has_permission(role: UserRole, permission: str) -> bool:
    return permission in _PERMISSIONS.get(role, set())
