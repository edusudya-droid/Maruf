"""Barcha jadvallarni async orqali yaratish — docker startup skripti."""
import asyncio
import sys
from loguru import logger


async def create_tables() -> None:
    # Modellarni import qilish (metadata to'ldirilishi uchun)
    import database.models  # noqa: F401

    from backend.core.database import engine, Base
    from database.models import Base as ModelsBase

    logger.info("Connecting to database...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(ModelsBase.metadata.create_all)
        logger.info("All tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_tables())
