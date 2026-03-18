"""Foydalanuvchilar API."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.api.dependencies import get_db, verify_admin
from database.models import User

router = APIRouter(prefix="/users", tags=["users"])


class UserUpdate(BaseModel):
    is_active: Optional[bool] = None
    user_role: Optional[str] = None
    language: Optional[str] = None
    format: Optional[str] = None
    topics: Optional[list[str]] = None


@router.get("/")
async def list_users(
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    conditions = []
    if is_active is not None:
        conditions.append(User.is_active == is_active)

    from sqlalchemy import and_
    result = await db.execute(
        select(User)
        .where(and_(*conditions) if conditions else True)
        .order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return [_user_dict(u) for u in users]


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_dict(user)


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    return _user_dict(user)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)


def _user_dict(u: User) -> dict:
    return {
        "id": u.id,
        "telegram_id": u.telegram_id,
        "username": u.username,
        "first_name": u.first_name,
        "user_role": u.user_role.value,
        "language": u.language.value,
        "format": u.format.value,
        "topics": u.topics,
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat(),
        "last_active_at": u.last_active_at.isoformat(),
    }
