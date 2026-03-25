"""
Telethon background monitor — rasmiy kanaldan yangi postlarni avtomatik saqlaydi.

Qilgan ishi:
- Rasmiy kanalga yangi post tushganda MTProto orqali qabul qiladi
- views_count ni HAQIQIY qiymat bilan source_posts ga saqlaydi
  (Bot API channel_post eventida views kelmaydi — shuning uchun doim 0 bo'lardi)
"""
import logging
from datetime import datetime, timezone

from telethon import TelegramClient, events

from config import settings as app_settings
from infrastructure.database.connection import AsyncSessionLocal
from infrastructure.repositories.post_repo import PostRepo
from infrastructure.telegram.client import is_telethon_configured, make_telethon_client

logger = logging.getLogger(__name__)


def _to_naive_utc(dt: datetime) -> datetime:
    """timezone-aware datetime → naive UTC (PostgreSQL TIMESTAMP WITHOUT TIME ZONE uchun)."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


async def start_channel_monitor() -> None:
    """
    Telethon kanal monitorini ishga tushiradi.
    bot/main.py da asyncio.gather() orqali parallel run qilinadi.
    """
    if not is_telethon_configured():
        logger.info(
            "Telethon sozlanmagan (TELEGRAM_API_ID / TELEGRAM_API_HASH / TELETHON_SESSION "
            "yo'q) — kanal monitoru o'chirilgan."
        )
        return

    client: TelegramClient = make_telethon_client()

    await client.connect()
    if not await client.is_user_authorized():
        logger.error(
            "Telethon session yaroqsiz yoki muddati o'tgan. "
            "Qayta autentifikatsiya: "
            "  docker-compose run --rm bot python -m infrastructure.telegram.generate_session"
        )
        await client.disconnect()
        return

    @client.on(events.NewMessage(chats=app_settings.official_channel_id))
    async def _on_new_post(event: events.NewMessage.Event) -> None:
        """Rasmiy kanaldan yangi post kelganda ishga tushadi."""
        msg = event.message
        views: int | None = getattr(msg, "views", None)

        logger.info(
            "Telethon: yangi post aniqlandi message_id=%s, views=%s",
            msg.id, views,
        )

        try:
            async with AsyncSessionLocal() as session:
                repo = PostRepo(session)
                channel = await repo.get_or_create_channel(
                    telegram_channel_id=app_settings.official_channel_id,
                    channel_title=getattr(event.chat, "title", "Official Channel"),
                    channel_url=app_settings.official_channel_url,
                )
                await repo.upsert(
                    official_channel_id=channel.id,
                    telegram_message_id=msg.id,
                    post_url=f"{app_settings.official_channel_url}/{msg.id}",
                    post_text=msg.text or getattr(msg, "message", None),
                    published_at=_to_naive_utc(msg.date),
                    views_count=views,
                    collected_at=_to_naive_utc(datetime.now(timezone.utc)),
                )
                await session.commit()
            logger.info(
                "Telethon: post saqlandi message_id=%s, views=%s",
                msg.id, views,
            )
        except Exception as exc:
            logger.exception("Telethon post saqlashda xato: %s", exc)

    logger.info(
        "Telethon kanal monitoru ishga tushdi (kanal: %s)",
        app_settings.official_channel_id,
    )
    await client.run_until_disconnected()
