from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import AuditLog, ErrorLog


class AuditLogRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        action_type: str,
        user_id: Optional[int] = None,
        object_type: Optional[str] = None,
        object_id: Optional[str] = None,
        details: Optional[str] = None,
    ) -> AuditLog:
        log = AuditLog(
            user_id=user_id,
            action_type=action_type,
            object_type=object_type,
            object_id=object_id,
            details=details,
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def list_recent(self, limit: int = 50) -> List[AuditLog]:
        result = await self.session.execute(
            select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())


class ErrorLogRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        error_code: str,
        error_message: str,
        analysis_run_id: Optional[int] = None,
        detected_post_id: Optional[int] = None,
    ) -> ErrorLog:
        log = ErrorLog(
            analysis_run_id=analysis_run_id,
            detected_post_id=detected_post_id,
            error_code=error_code,
            error_message=error_message,
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def list_for_run(self, analysis_run_id: int) -> List[ErrorLog]:
        result = await self.session.execute(
            select(ErrorLog)
            .where(ErrorLog.analysis_run_id == analysis_run_id)
            .order_by(ErrorLog.created_at.asc())
        )
        return list(result.scalars().all())
