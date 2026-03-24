from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import SystemSetting


class SettingsRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, key: str) -> Optional[SystemSetting]:
        result = await self.session.execute(
            select(SystemSetting).where(SystemSetting.setting_key == key)
        )
        return result.scalar_one_or_none()

    async def get_value(self, key: str, default: str = "") -> str:
        setting = await self.get(key)
        return setting.setting_value if setting else default

    async def list_all(self) -> List[SystemSetting]:
        result = await self.session.execute(
            select(SystemSetting).order_by(SystemSetting.setting_key)
        )
        return list(result.scalars().all())

    async def set(self, key: str, value: str, updated_by_user_id: Optional[int] = None) -> None:
        existing = await self.get(key)
        if existing:
            await self.session.execute(
                update(SystemSetting)
                .where(SystemSetting.setting_key == key)
                .values(setting_value=value, updated_by_user_id=updated_by_user_id)
            )
        else:
            setting = SystemSetting(
                setting_key=key,
                setting_value=value,
                updated_by_user_id=updated_by_user_id,
            )
            self.session.add(setting)
