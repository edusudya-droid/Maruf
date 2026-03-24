from typing import Optional, List

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import User


class UserRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_user_id: int) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def list_all(self) -> List[User]:
        result = await self.session.execute(select(User).order_by(User.created_at.desc()))
        return list(result.scalars().all())

    async def count_active(self) -> int:
        result = await self.session.execute(
            select(User).where(User.status == "ACTIVE")
        )
        return len(result.scalars().all())

    async def create(
        self,
        telegram_user_id: int,
        full_name: Optional[str],
        username: Optional[str],
        role: str,
    ) -> User:
        user = User(
            telegram_user_id=telegram_user_id,
            full_name=full_name,
            username=username,
            role=role,
            status="ACTIVE",
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def update_status(self, user_id: int, status: str) -> None:
        await self.session.execute(
            update(User).where(User.id == user_id).values(status=status)
        )

    async def update_role(self, user_id: int, role: str) -> None:
        await self.session.execute(
            update(User).where(User.id == user_id).values(role=role)
        )
