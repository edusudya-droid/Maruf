"""
Post service — rasmiy kanal postlarini boshqarish.

MUHIM: Bot API orqali kanal tarixini olish mumkin emas (aiogram 3.x da
get_chat_history() metodi mavjud emas). Postlar quyidagi yo'llar bilan saqlanadi:
  1. Avtomatik — channel_listener.py (Telethon) yangi postlarni real-time ushlaydi
  2. Qo'lda    — admin postni botga forward qiladi (posts.py handler)
  3. Retrospektiv — Telethon orqali kanal tarixini batch olish (telethon_sync funksiyasi)
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings as app_settings
from domain.exceptions import (
    OfficialChannelNotConfiguredError,
    PostNotFoundError,
    PostsFetchFailedError,
    ok,
    err,
)
from infrastructure.repositories.post_repo import PostRepo

logger = logging.getLogger(__name__)


async def fetch_and_store_recent_posts(session: AsyncSession) -> dict:
    """
    Rasmiy kanalning so'nggi postlarini Telethon orqali oladi va DB ga saqlaydi.

    Agar Telethon sozlanmagan bo'lsa — mavjud DB postlarini qaytaradi.
    """
    from infrastructure.telegram.client import is_telethon_configured, make_telethon_client
    from infrastructure.telegram.repost_finder import get_message_views

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
        logger.error("OfficialChannel yaratishda xato: %s", exc)
        return err(OfficialChannelNotConfiguredError(str(exc)))

    if not is_telethon_configured():
        # Telethon yo'q — faqat mavjud postlarni qaytaramiz
        logger.info(
            "Telethon sozlanmagan — DB dagi mavjud %d ta post qaytariladi",
            limit,
        )
        posts = await repo.list_recent(channel.id, limit=limit)
        return ok(data=posts)

    # Telethon orqali kanal tarixini olish
    client = make_telethon_client()
    posts_saved = []

    try:
        await client.connect()
        if not await client.is_user_authorized():
            logger.error("Telethon session yaroqsiz — DB dagi postlar qaytariladi")
            posts = await repo.list_recent(channel.id, limit=limit)
            return ok(data=posts)

        collected_at_naive = datetime.now(timezone.utc).replace(tzinfo=None)

        async for msg in client.iter_messages(channel_id, limit=limit):
            if not msg or not msg.date:
                continue

            msg_date = msg.date
            if msg_date.tzinfo is None:
                msg_date = msg_date.replace(tzinfo=timezone.utc)

            def _to_naive(dt: datetime) -> datetime:
                return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt

            try:
                post = await repo.upsert(
                    official_channel_id=channel.id,
                    telegram_message_id=msg.id,
                    post_url=f"{channel_url}/{msg.id}",
                    post_text=msg.text or getattr(msg, "message", None),
                    published_at=_to_naive(msg_date),
                    views_count=getattr(msg, "views", None),
                    collected_at=collected_at_naive,
                )
                posts_saved.append(post)
            except Exception as exc:
                logger.warning("Post msg_id=%s saqlashda xato: %s", msg.id, exc)
                continue

        await session.commit()
        logger.info(
            "Telethon orqali %d ta post saqlandi/yangilandi", len(posts_saved)
        )
        return ok(data=posts_saved)

    except Exception as exc:
        logger.exception("Telethon kanal tarixini olishda xato: %s", exc)
        # Fallback: mavjud postlarni qaytaramiz
        try:
            posts = await repo.list_recent(channel.id, limit=limit)
            return ok(data=posts)
        except Exception:
            return err(PostsFetchFailedError(str(exc)))
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


async def get_recent_posts(session: AsyncSession) -> dict:
    """DB dagi so'nggi postlarni qaytaradi."""
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
        return err(PostNotFoundError())
    return ok(data=post)
