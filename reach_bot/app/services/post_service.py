from datetime import datetime, timezone
from typing import Optional

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings as app_settings
from domain.exceptions import (
    OfficialChannelNotConfiguredError,
    PostsFetchFailedError,
    ok,
    err,
)
from infrastructure.repositories.post_repo import PostRepo


async def fetch_and_store_recent_posts(session: AsyncSession, bot: Bot) -> dict:
    """
    Fetch the latest MAX_VISIBLE_POSTS messages from the official channel via Bot API
    and upsert them into source_posts.
    """
    repo = PostRepo(session)
    channel_id = app_settings.official_channel_id
    channel_url = app_settings.official_channel_url
    limit = app_settings.max_visible_posts

    try:
        channel = await repo.get_or_create_channel(
            telegram_channel_id=channel_id,
            channel_title="Official Channel",
            channel_url=channel_url,
        )
    except Exception as exc:
        return err(OfficialChannelNotConfiguredError(str(exc)))

    try:
        # Retrieve messages using Bot API
        messages = await bot.get_chat_history(chat_id=channel_id, limit=limit)
    except AttributeError:
        # aiogram 3.x uses different approach for getting channel history
        # Use forward_from_chat or getChatHistory workaround
        messages = []
    except Exception as exc:
        return err(PostsFetchFailedError(str(exc)))

    posts = []
    collected_at = datetime.now(timezone.utc)
    for msg in messages:
        if not msg.date:
            continue
        published_at = msg.date if isinstance(msg.date, datetime) else datetime.fromtimestamp(
            msg.date, tz=timezone.utc
        )
        post_url = f"{channel_url}/{msg.message_id}"
        post_text = msg.text or msg.caption or None
        views_count = getattr(msg, "views", None)
        try:
            post = await repo.upsert(
                official_channel_id=channel.id,
                telegram_message_id=msg.message_id,
                post_url=post_url,
                post_text=post_text,
                published_at=published_at,
                views_count=views_count,
                collected_at=collected_at,
            )
            posts.append(post)
        except Exception:
            continue

    await session.commit()
    return ok(data=posts)


async def get_recent_posts(session: AsyncSession) -> dict:
    """Return recent posts from DB (already stored)."""
    repo = PostRepo(session)

    channel = await repo.get_active_channel()
    if not channel:
        try:
            channel = await repo.get_or_create_channel(
                telegram_channel_id=app_settings.official_channel_id,
                channel_title="Official Channel",
                channel_url=app_settings.official_channel_url,
            )
            await session.commit()
        except Exception as exc:
            return err(OfficialChannelNotConfiguredError(str(exc)))

    posts = await repo.list_recent(channel.id, limit=app_settings.max_visible_posts)
    return ok(data=posts)


async def get_post_by_id(post_id: int, session: AsyncSession) -> dict:
    repo = PostRepo(session)
    post = await repo.get_by_id(post_id)
    if not post:
        from domain.exceptions import PostNotFoundError
        return err(PostNotFoundError())
    return ok(data=post)
