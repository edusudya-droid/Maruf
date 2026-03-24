from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import OfficialChannel, SourcePost


class PostRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_channel(self) -> Optional[OfficialChannel]:
        result = await self.session.execute(
            select(OfficialChannel).where(OfficialChannel.is_active.is_(True)).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_or_create_channel(
        self,
        telegram_channel_id: int,
        channel_title: str,
        channel_url: str,
    ) -> OfficialChannel:
        existing = await self.session.execute(
            select(OfficialChannel).where(
                OfficialChannel.telegram_channel_id == telegram_channel_id
            )
        )
        channel = existing.scalar_one_or_none()
        if channel:
            return channel
        channel = OfficialChannel(
            telegram_channel_id=telegram_channel_id,
            channel_title=channel_title,
            channel_url=channel_url,
            is_active=True,
        )
        self.session.add(channel)
        await self.session.flush()
        await self.session.refresh(channel)
        return channel

    async def list_recent(self, channel_id: int, limit: int = 20) -> List[SourcePost]:
        result = await self.session.execute(
            select(SourcePost)
            .where(SourcePost.official_channel_id == channel_id)
            .order_by(SourcePost.published_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_id(self, post_id: int) -> Optional[SourcePost]:
        result = await self.session.execute(
            select(SourcePost).where(SourcePost.id == post_id)
        )
        return result.scalar_one_or_none()

    async def get_by_message_id(
        self, channel_id: int, message_id: int
    ) -> Optional[SourcePost]:
        result = await self.session.execute(
            select(SourcePost).where(
                SourcePost.official_channel_id == channel_id,
                SourcePost.telegram_message_id == message_id,
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        official_channel_id: int,
        telegram_message_id: int,
        post_url: str,
        post_text: Optional[str],
        published_at: datetime,
        views_count: Optional[int],
        collected_at: datetime,
    ) -> SourcePost:
        existing = await self.get_by_message_id(official_channel_id, telegram_message_id)
        if existing:
            existing.views_count = views_count
            existing.collected_at = collected_at
            await self.session.flush()
            return existing
        post = SourcePost(
            official_channel_id=official_channel_id,
            telegram_message_id=telegram_message_id,
            post_url=post_url,
            post_text=post_text,
            published_at=published_at,
            views_count=views_count,
            collected_at=collected_at,
        )
        self.session.add(post)
        await self.session.flush()
        await self.session.refresh(post)
        return post
