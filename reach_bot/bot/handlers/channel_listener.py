from datetime import datetime, timezone

from aiogram import Router
from aiogram.types import Message

from config import settings as app_settings
from infrastructure.database.connection import AsyncSessionLocal
from infrastructure.repositories.post_repo import PostRepo

router = Router()


@router.channel_post()
async def on_channel_post(message: Message) -> None:
    if message.chat.id != app_settings.official_channel_id:
        return

    async with AsyncSessionLocal() as session:
        repo = PostRepo(session)
        channel = await repo.get_or_create_channel(
            telegram_channel_id=message.chat.id,
            channel_title=message.chat.title or "Official Channel",
            channel_url=app_settings.official_channel_url,
        )
        post_url = f"{app_settings.official_channel_url}/{message.message_id}"
        published_at = (
            message.date
            if isinstance(message.date, datetime)
            else datetime.fromtimestamp(message.date, tz=timezone.utc)
        )
        await repo.upsert(
            official_channel_id=channel.id,
            telegram_message_id=message.message_id,
            post_url=post_url,
            post_text=message.text or message.caption,
            published_at=published_at,
            views_count=getattr(message, "views", None),
            collected_at=datetime.now(timezone.utc),
        )
        await session.commit()
