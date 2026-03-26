from typing import Optional

from telethon import TelegramClient
from telethon.sessions import StringSession

from config import settings as app_settings


def make_telethon_client() -> Optional[TelegramClient]:
    """
    Yangi TelegramClient (MTProto user client) yaratadi.
    Agar sozlamalar to'liq bo'lmasa — None qaytaradi.
    """
    if not app_settings.telegram_api_id or not app_settings.telegram_api_hash:
        return None
    return TelegramClient(
        StringSession(app_settings.telethon_session or ""),
        app_settings.telegram_api_id,
        app_settings.telegram_api_hash,
    )


def is_telethon_configured() -> bool:
    """Telethon sozlamalari to'liq kiritilganmi."""
    return bool(
        app_settings.telegram_api_id
        and app_settings.telegram_api_hash
        and app_settings.telethon_session
    )
