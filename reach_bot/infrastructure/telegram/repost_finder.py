"""
Telethon orqali repostlarni qidirish va post ko'rishlarini olish.

Bot API views ni qaytarmaydi — bu muammoni faqat MTProto hal qiladi.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from telethon import TelegramClient
from telethon.errors import (
    ChannelPrivateError,
    ChatAdminRequiredError,
    FloodWaitError,
    UserNotParticipantError,
)

logger = logging.getLogger(__name__)


def _raw_channel_id(bot_api_id: int) -> int:
    """
    Bot API kanal ID sini Telethon raw channel_id ga o'tkazadi.
    Bot API format: -100XXXXXXXXX  →  Telethon: XXXXXXXXX
    """
    if bot_api_id < 0:
        return int(str(abs(bot_api_id))[3:])
    return bot_api_id


async def get_message_views(
    client: TelegramClient,
    channel_bot_api_id: int,
    message_id: int,
) -> Optional[int]:
    """
    Kanal postining haqiqiy ko'rishlar sonini MTProto orqali oladi.
    Bot API bu ma'lumotni qaytarmaydi.
    """
    try:
        msg = await client.get_messages(channel_bot_api_id, ids=message_id)
        if msg:
            views = getattr(msg, "views", None)
            logger.debug(
                "get_message_views: channel=%s, msg_id=%s → views=%s",
                channel_bot_api_id, message_id, views,
            )
            return views
    except Exception as exc:
        logger.warning("get_message_views xato (channel=%s, msg=%s): %s", channel_bot_api_id, message_id, exc)
    return None


async def find_reposts(
    client: TelegramClient,
    official_channel_bot_api_id: int,
    source_message_id: int,
    days_back: int = 30,
    max_channels: int = 300,
) -> List[Dict[str, Any]]:
    """
    Barcha mavjud kanallarda berilgan postning repostlarini qidiradi.

    Repost sifatida hisoblanadi:
    - msg.fwd_from.channel_id == rasmiy kanal raw ID
    - msg.fwd_from.channel_post == manba message_id

    Natija: har biri bo'yicha dict (post_url, views_count, channel_name, ...)
    """
    raw_official_id = _raw_channel_id(official_channel_bot_api_id)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    candidates: List[Dict[str, Any]] = []
    checked = 0

    logger.info(
        "find_reposts boshlandi: rasmiy_kanal=%s (raw=%s), msg_id=%s, max_channels=%d, days_back=%d",
        official_channel_bot_api_id, raw_official_id, source_message_id, max_channels, days_back,
    )

    async for dialog in client.iter_dialogs():
        if checked >= max_channels:
            break

        # Faqat kanallarni tekshirish (guruhlar va DM lar emas)
        if not dialog.is_channel:
            continue

        entity = dialog.entity
        # Rasmiy kanalni o'zi o'tkazib yuborish
        if entity.id == raw_official_id:
            continue

        checked += 1
        channel_title = getattr(entity, "title", f"channel_{entity.id}")
        channel_username = getattr(entity, "username", None)

        try:
            async for msg in client.iter_messages(entity, limit=200):
                if not msg or not msg.date:
                    continue

                msg_date = msg.date
                if msg_date.tzinfo is None:
                    msg_date = msg_date.replace(tzinfo=timezone.utc)

                # Eski xabardan keyin to'xtash (xabarlar yangi→eski tartibda keladi)
                if msg_date < cutoff:
                    break

                if not msg.fwd_from:
                    continue

                fwd_channel_id = getattr(msg.fwd_from, "channel_id", None)
                fwd_post_id = getattr(msg.fwd_from, "channel_post", None)

                if fwd_channel_id == raw_official_id and fwd_post_id == source_message_id:
                    post_url = (
                        f"https://t.me/{channel_username}/{msg.id}"
                        if channel_username
                        else None
                    )
                    views = getattr(msg, "views", None) or 0
                    candidates.append({
                        "post_url": post_url,
                        "channel_id": dialog.id,
                        "message_id": msg.id,
                        "text": msg.text or getattr(msg, "message", None),
                        "views_count": views,
                        "channel_name": channel_title,
                        "is_forward": True,
                        "has_source_link": False,
                        "published_at": msg_date,
                    })
                    logger.info(
                        "Repost topildi: %s (msg=%s), views=%s",
                        channel_title, msg.id, views,
                    )

        except FloodWaitError as exc:
            wait = min(exc.seconds, 60)
            logger.warning("FloodWait %ds — %s kutilmoqda", wait, channel_title)
            await asyncio.sleep(wait)
        except (ChannelPrivateError, ChatAdminRequiredError, UserNotParticipantError):
            pass  # yopiq kanal — o'tkazib yuboriladi
        except Exception as exc:
            logger.debug("Dialog %s tekshirishda xato: %s", channel_title, exc)

    logger.info(
        "find_reposts tugadi: %d ta kanal tekshirildi, %d ta repost topildi",
        checked, len(candidates),
    )
    return candidates
