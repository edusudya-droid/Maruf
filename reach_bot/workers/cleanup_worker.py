"""
Cleanup worker — removes old analysis runs based on history_retention_days setting.
Runs as a periodic Celery beat task.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from infrastructure.database.connection import AsyncSessionLocal
from infrastructure.database.models import AnalysisRun
from infrastructure.repositories.settings_repo import SettingsRepo
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="workers.cleanup_worker.cleanup_old_runs")
def cleanup_old_runs() -> None:
    asyncio.run(_cleanup_async())


async def _cleanup_async() -> None:
    async with AsyncSessionLocal() as session:
        settings_repo = SettingsRepo(session)
        retention_value = await settings_repo.get_value("history_retention_days", "null")

        if retention_value == "null":
            logger.info("History retention: unlimited — skipping cleanup")
            return

        try:
            days = int(retention_value)
        except ValueError:
            logger.warning("Invalid history_retention_days value: %s", retention_value)
            return

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await session.execute(
            select(AnalysisRun.id).where(AnalysisRun.started_at < cutoff)
        )
        old_ids = [row[0] for row in result.fetchall()]

        if not old_ids:
            return

        await session.execute(
            delete(AnalysisRun).where(AnalysisRun.id.in_(old_ids))
        )
        await session.commit()
        logger.info("Cleaned up %d old analysis runs (older than %d days)", len(old_ids), days)


# Periodic schedule (configure in Celery beat settings if needed)
celery_app.conf.beat_schedule = {
    "cleanup-old-runs-daily": {
        "task": "workers.cleanup_worker.cleanup_old_runs",
        "schedule": 86400,  # every 24 hours
    },
}
