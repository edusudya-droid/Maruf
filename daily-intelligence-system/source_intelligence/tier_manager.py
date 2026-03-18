"""Tier boshqaruvi — manba tier'larini ko'rish va o'zgartirish."""
from loguru import logger
from sqlalchemy import select
from backend.core.database import AsyncSessionLocal
from database.models import Source


async def get_sources_by_tier(tier: int) -> list[Source]:
    """Berilgan tier bo'yicha manbalarni olish."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Source).where(Source.tier == tier, Source.is_active == True)
        )
        return result.scalars().all()


async def promote_source(source_id: int) -> bool:
    """Manba tier'ini bir ko'tarish (masalan, 3 → 2)."""
    async with AsyncSessionLocal() as session:
        source = await session.get(Source, source_id)
        if not source:
            return False
        if source.tier > 1:
            source.tier -= 1
            await session.commit()
            logger.info(f"Source {source.name} promoted to tier {source.tier}")
            return True
    return False


async def demote_source(source_id: int) -> bool:
    """Manba tier'ini bir tushirish."""
    async with AsyncSessionLocal() as session:
        source = await session.get(Source, source_id)
        if not source:
            return False
        if source.tier < 5:
            source.tier += 1
            await session.commit()
            logger.info(f"Source {source.name} demoted to tier {source.tier}")
            return True
    return False
