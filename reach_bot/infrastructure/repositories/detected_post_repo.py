from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import DetectedPost


class DetectedPostRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        analysis_run_id: int,
        source_post_id: int,
        status: str,
        external_channel_name: Optional[str] = None,
        external_channel_id: Optional[int] = None,
        telegram_message_id: Optional[int] = None,
        post_url: Optional[str] = None,
        post_text: Optional[str] = None,
        published_at=None,
        views_count: Optional[int] = None,
        confirmation_type: Optional[str] = None,
        skip_reason: Optional[str] = None,
        text_similarity_score: Optional[float] = None,
    ) -> DetectedPost:
        dp = DetectedPost(
            analysis_run_id=analysis_run_id,
            source_post_id=source_post_id,
            external_channel_name=external_channel_name,
            external_channel_id=external_channel_id,
            telegram_message_id=telegram_message_id,
            post_url=post_url,
            post_text=post_text,
            published_at=published_at,
            views_count=views_count,
            confirmation_type=confirmation_type,
            status=status,
            skip_reason=skip_reason,
            text_similarity_score=text_similarity_score,
        )
        self.session.add(dp)
        await self.session.flush()
        await self.session.refresh(dp)
        return dp

    async def list_for_run(self, analysis_run_id: int) -> List[DetectedPost]:
        result = await self.session.execute(
            select(DetectedPost)
            .where(DetectedPost.analysis_run_id == analysis_run_id)
            .order_by(DetectedPost.created_at.asc())
        )
        return list(result.scalars().all())

    async def exists_by_url(self, analysis_run_id: int, post_url: str) -> bool:
        result = await self.session.execute(
            select(DetectedPost).where(
                DetectedPost.analysis_run_id == analysis_run_id,
                DetectedPost.post_url == post_url,
            )
        )
        return result.scalar_one_or_none() is not None

    async def exists_by_message_id(
        self, analysis_run_id: int, channel_id: int, message_id: int
    ) -> bool:
        result = await self.session.execute(
            select(DetectedPost).where(
                DetectedPost.analysis_run_id == analysis_run_id,
                DetectedPost.external_channel_id == channel_id,
                DetectedPost.telegram_message_id == message_id,
            )
        )
        return result.scalar_one_or_none() is not None
