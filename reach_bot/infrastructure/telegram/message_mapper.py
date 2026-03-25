"""
Telethon message → unified candidate format converter.

Barcha qidiruv usullari (FORWARD, SOURCE_LINK, TEXT_COPY, NEAR_TEXT_COPY)
bir xil formatda natija qaytarishi uchun.
"""
import json
from datetime import timezone
from typing import Any, Dict, Optional


class DiscoveryMethod:
    PUBLIC_FORWARD = "PUBLIC_FORWARD"
    SOURCE_LINK = "SOURCE_LINK"
    TEXT_COPY = "TEXT_COPY"
    NEAR_TEXT_COPY = "NEAR_TEXT_COPY"


def map_telethon_message(
    msg: Any,
    dialog: Any,
    discovery_method: str,
    has_source_link: bool = False,
) -> Dict[str, Any]:
    """
    Telethon Message + Dialog → unified candidate dict.

    Qaytariladigan format analysis_worker._process_candidate()
    va detected_post_repo.create() bilan to'liq mos.
    """
    channel_username: Optional[str] = getattr(dialog.entity, "username", None)
    channel_name: str = getattr(dialog.entity, "title", f"channel_{dialog.id}")

    post_url: Optional[str] = (
        f"https://t.me/{channel_username}/{msg.id}" if channel_username else None
    )

    msg_date = msg.date
    if msg_date and msg_date.tzinfo is None:
        msg_date = msg_date.replace(tzinfo=timezone.utc)

    # Raw metadata — debugging uchun
    fwd_info = None
    if getattr(msg, "fwd_from", None):
        fwd_info = {
            "channel_id": getattr(msg.fwd_from, "channel_id", None),
            "channel_post": getattr(msg.fwd_from, "channel_post", None),
        }

    raw_metadata = json.dumps(
        {"discovery_method": discovery_method, "fwd_from": fwd_info},
        default=str,
    )

    return {
        "channel_id": dialog.id,
        "channel_username": channel_username,
        "channel_name": channel_name,
        "message_id": msg.id,
        "post_url": post_url,
        "text": msg.text or getattr(msg, "message", None),
        "views_count": getattr(msg, "views", None) or 0,
        "published_at": msg_date,
        "is_forward": bool(getattr(msg, "fwd_from", None)),
        "has_source_link": has_source_link,
        "discovery_method": discovery_method,
        "raw_metadata": raw_metadata,
    }
