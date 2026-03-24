from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings as app_settings
from domain.enums import UserRole, UserStatus
from domain.exceptions import (
    InvalidRoleError,
    UserAlreadyExistsError,
    UserNotFoundError,
    ok,
    err,
)
from infrastructure.repositories.log_repo import AuditLogRepo
from infrastructure.repositories.user_repo import UserRepo


async def add_user(
    telegram_user_id: int,
    role: str,
    full_name: Optional[str],
    username: Optional[str],
    session: AsyncSession,
    performed_by_user_id: Optional[int] = None,
) -> dict:
    try:
        role_enum = UserRole(role)
    except ValueError:
        return err(InvalidRoleError(f"Noto'g'ri rol: {role}"))

    repo = UserRepo(session)
    existing = await repo.get_by_telegram_id(telegram_user_id)
    if existing:
        return err(UserAlreadyExistsError())

    user = await repo.create(
        telegram_user_id=telegram_user_id,
        full_name=full_name,
        username=username,
        role=role_enum.value,
    )
    log_repo = AuditLogRepo(session)
    await log_repo.create(
        action_type="USER_CREATED",
        user_id=performed_by_user_id,
        object_type="User",
        object_id=str(telegram_user_id),
        details=f"Role: {role_enum.value}",
    )
    await session.commit()
    return ok(data={"id": user.id, "telegram_user_id": user.telegram_user_id, "role": user.role})


async def set_user_status(
    target_user_id: int,
    status: str,
    session: AsyncSession,
    performed_by_user_id: Optional[int] = None,
) -> dict:
    repo = UserRepo(session)
    user = await repo.get_by_id(target_user_id)
    if not user:
        return err(UserNotFoundError())

    action = "USER_BLOCKED" if status == "BLOCKED" else "USER_UNBLOCKED"
    await repo.update_status(target_user_id, status)

    log_repo = AuditLogRepo(session)
    await log_repo.create(
        action_type=action,
        user_id=performed_by_user_id,
        object_type="User",
        object_id=str(target_user_id),
    )
    await session.commit()
    return ok()


async def change_role(
    target_user_id: int,
    new_role: str,
    session: AsyncSession,
    performed_by_user_id: Optional[int] = None,
) -> dict:
    try:
        role_enum = UserRole(new_role)
    except ValueError:
        return err(InvalidRoleError())

    repo = UserRepo(session)
    user = await repo.get_by_id(target_user_id)
    if not user:
        return err(UserNotFoundError())

    await repo.update_role(target_user_id, role_enum.value)
    log_repo = AuditLogRepo(session)
    await log_repo.create(
        action_type="USER_ROLE_CHANGED",
        user_id=performed_by_user_id,
        object_type="User",
        object_id=str(target_user_id),
        details=f"New role: {role_enum.value}",
    )
    await session.commit()
    return ok()


async def list_users(session: AsyncSession) -> dict:
    repo = UserRepo(session)
    users = await repo.list_all()
    return ok(data=[
        {
            "id": u.id,
            "telegram_user_id": u.telegram_user_id,
            "full_name": u.full_name,
            "username": u.username,
            "role": u.role,
            "status": u.status,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ])
