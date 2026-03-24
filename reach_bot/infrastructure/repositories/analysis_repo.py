from datetime import date, datetime, timezone
from typing import List, Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import AnalysisRun


class AnalysisRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, source_post_id: int, started_by_user_id: int) -> AnalysisRun:
        run = AnalysisRun(
            source_post_id=source_post_id,
            started_by_user_id=started_by_user_id,
            status="PENDING",
        )
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_by_id(self, run_id: int) -> Optional[AnalysisRun]:
        result = await self.session.execute(
            select(AnalysisRun).where(AnalysisRun.id == run_id)
        )
        return result.scalar_one_or_none()

    async def get_running_for_post(self, source_post_id: int) -> Optional[AnalysisRun]:
        result = await self.session.execute(
            select(AnalysisRun).where(
                AnalysisRun.source_post_id == source_post_id,
                AnalysisRun.status.in_(["PENDING", "RUNNING"]),
            )
        )
        return result.scalar_one_or_none()

    async def get_running_for_user(self, user_id: int) -> Optional[AnalysisRun]:
        result = await self.session.execute(
            select(AnalysisRun).where(
                AnalysisRun.started_by_user_id == user_id,
                AnalysisRun.status.in_(["PENDING", "RUNNING"]),
            )
        )
        return result.scalar_one_or_none()

    async def count_today(self) -> int:
        today_start = datetime.combine(date.today(), datetime.min.time())
        result = await self.session.execute(
            select(func.count(AnalysisRun.id)).where(
                AnalysisRun.started_at >= today_start,
                AnalysisRun.status != "FAILED",
            )
        )
        return result.scalar_one() or 0

    async def update_status(self, run_id: int, status: str) -> None:
        values: dict = {"status": status}
        if status in ("COMPLETED", "COMPLETED_WITH_SKIPS", "FAILED"):
            values["finished_at"] = datetime.now(timezone.utc)
        await self.session.execute(
            update(AnalysisRun).where(AnalysisRun.id == run_id).values(**values)
        )

    async def update_results(
        self,
        run_id: int,
        status: str,
        source_views: int,
        confirmed_secondary_views: int,
        total_confirmed_reach: int,
        counted_posts_count: int,
        skipped_posts_count: int,
        notes: Optional[str] = None,
    ) -> None:
        await self.session.execute(
            update(AnalysisRun)
            .where(AnalysisRun.id == run_id)
            .values(
                status=status,
                finished_at=datetime.now(timezone.utc),
                source_views=source_views,
                confirmed_secondary_views=confirmed_secondary_views,
                total_confirmed_reach=total_confirmed_reach,
                counted_posts_count=counted_posts_count,
                skipped_posts_count=skipped_posts_count,
                notes=notes,
            )
        )

    async def list_for_post(self, source_post_id: int) -> List[AnalysisRun]:
        result = await self.session.execute(
            select(AnalysisRun)
            .where(AnalysisRun.source_post_id == source_post_id)
            .order_by(AnalysisRun.started_at.desc())
        )
        return list(result.scalars().all())

    async def list_all(self, limit: int = 50) -> List[AnalysisRun]:
        result = await self.session.execute(
            select(AnalysisRun).order_by(AnalysisRun.started_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
