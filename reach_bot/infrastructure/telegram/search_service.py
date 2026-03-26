"""
SearchService — rasmiy kanal postining vторichный tarqalishlarini qidiradi.

4 ta usul:
  1. PUBLIC_FORWARD   — fwd_from.channel_id + fwd_from.channel_post tekshiruvi
  2. SOURCE_LINK      — message.text da rasmiy kanal URL si borligi
  3. TEXT_COPY        — matn o'xshashligi == 1.0 (to'liq nusxa)
  4. NEAR_TEXT_COPY   — matn o'xshashligi >= threshold

CHEKLOV: Faqat Telethon akkaunti a'zo bo'lgan kanallarda qidiriladi.
Butun Telegram da qidirish API qoida buzilishi hisoblanadi.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

from telethon import TelegramClient
from telethon.errors import (
    ChannelPrivateError,
    ChatAdminRequiredError,
    FloodWaitError,
    UserNotParticipantError,
)

from domain.algorithms.text_normalizer import normalize
from domain.algorithms.text_comparator import similarity_score
from infrastructure.telegram.message_mapper import DiscoveryMethod, map_telethon_message

logger = logging.getLogger(__name__)


def _raw_channel_id(bot_api_id: int) -> int:
    """Bot API -100XXXXXXXXX → Telethon raw channel_id XXXXXXXXX."""
    if bot_api_id < 0:
        return int(str(abs(bot_api_id))[3:])
    return bot_api_id


def _contains_source_link(text: str, official_channel_url: str, source_msg_url: str) -> bool:
    """Matnda rasmiy kanal havolasi borligini tekshiradi."""
    if not text:
        return False
    text_lower = text.lower()
    return (
        official_channel_url.lower() in text_lower
        or source_msg_url.lower() in text_lower
    )


class SearchService:
    """
    Rasmiy kanal postining barcha tarqalishlarini qidiruvchi servis.

    Ishlatish:
        async with client:
            service = SearchService(...)
            candidates = await service.search_all()
    """

    def __init__(
        self,
        client: TelegramClient,
        official_channel_bot_api_id: int,
        source_message_id: int,
        source_text: str,
        official_channel_url: str,
        source_message_url: str,
        similarity_threshold: float = 0.90,
        days_back: int = 30,
        max_channels: int = 300,
    ) -> None:
        self._client = client
        self._raw_official_id = _raw_channel_id(official_channel_bot_api_id)
        self._bot_api_official_id = official_channel_bot_api_id
        self._source_msg_id = source_message_id
        self._source_text = source_text
        self._normalized_source = normalize(source_text) if source_text.strip() else ""
        self._official_channel_url = official_channel_url.rstrip("/")
        self._source_msg_url = source_message_url
        self._threshold = similarity_threshold
        self._cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        self._max_channels = max_channels

        # Deduplikatsiya uchun
        self._seen: set = set()

    async def search_all(self) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        Barcha 4 usul bilan qidiradi.
        Qaytaradi: (candidates_list, method_counts_dict)
        """
        candidates: List[Dict[str, Any]] = []
        counts = {
            DiscoveryMethod.PUBLIC_FORWARD: 0,
            DiscoveryMethod.SOURCE_LINK: 0,
            DiscoveryMethod.TEXT_COPY: 0,
            DiscoveryMethod.NEAR_TEXT_COPY: 0,
        }
        checked = 0

        logger.info(
            "SearchService: qidiruv boshlandi | raw_official=%s, msg_id=%s, "
            "threshold=%.2f, days=%d, max_channels=%d",
            self._raw_official_id,
            self._source_msg_id,
            self._threshold,
            (datetime.now(timezone.utc) - self._cutoff).days,
            self._max_channels,
        )

        async for dialog in self._client.iter_dialogs():
            if checked >= self._max_channels:
                break
            if not dialog.is_channel:
                continue
            # Rasmiy kanalni o'zi o'tkazib yuborish
            if dialog.entity.id == self._raw_official_id:
                continue

            checked += 1

            try:
                new_candidates, new_counts = await self._check_channel(dialog)
                candidates.extend(new_candidates)
                for method, cnt in new_counts.items():
                    counts[method] = counts.get(method, 0) + cnt
            except FloodWaitError as exc:
                wait = min(exc.seconds, 60)
                logger.warning(
                    "FloodWait %ds — %s kutilmoqda",
                    wait,
                    getattr(dialog.entity, "title", dialog.id),
                )
                await asyncio.sleep(wait)
            except (ChannelPrivateError, ChatAdminRequiredError, UserNotParticipantError):
                pass
            except Exception as exc:
                logger.debug(
                    "Kanal %s tekshirishda xato: %s",
                    getattr(dialog.entity, "title", dialog.id),
                    exc,
                )

        logger.info(
            "SearchService: %d kanal tekshirildi | FORWARD=%d, SOURCE_LINK=%d, "
            "TEXT_COPY=%d, NEAR_TEXT_COPY=%d | jami=%d",
            checked,
            counts[DiscoveryMethod.PUBLIC_FORWARD],
            counts[DiscoveryMethod.SOURCE_LINK],
            counts[DiscoveryMethod.TEXT_COPY],
            counts[DiscoveryMethod.NEAR_TEXT_COPY],
            len(candidates),
        )
        return candidates, counts

    async def _check_channel(
        self, dialog: Any
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """Bitta kanalda barcha metodlarni qo'llaydi."""
        candidates = []
        counts: Dict[str, int] = {}

        async for msg in self._client.iter_messages(dialog.entity, limit=200):
            if not msg or not msg.date:
                continue

            msg_date = msg.date
            if msg_date.tzinfo is None:
                msg_date = msg_date.replace(tzinfo=timezone.utc)

            if msg_date < self._cutoff:
                break  # xabarlar yangi→eski tartibda

            dedup_key = (dialog.id, msg.id)
            if dedup_key in self._seen:
                continue

            method = self._detect_method(msg)
            if method is None:
                continue

            self._seen.add(dedup_key)
            has_link = method == DiscoveryMethod.SOURCE_LINK

            candidate = map_telethon_message(
                msg=msg,
                dialog=dialog,
                discovery_method=method,
                has_source_link=has_link,
            )
            candidates.append(candidate)
            counts[method] = counts.get(method, 0) + 1

            logger.debug(
                "[%s] %s → msg=%s, views=%s",
                method,
                getattr(dialog.entity, "title", dialog.id),
                msg.id,
                candidate["views_count"],
            )

        return candidates, counts

    def _detect_method(self, msg: Any) -> str | None:
        """
        Xabar qaysi usulga kiradi?
        Prioritet: FORWARD > SOURCE_LINK > TEXT_COPY > NEAR_TEXT_COPY
        """
        # 1. PUBLIC_FORWARD
        fwd = getattr(msg, "fwd_from", None)
        if fwd:
            fwd_ch_id = getattr(fwd, "channel_id", None)
            fwd_post_id = getattr(fwd, "channel_post", None)
            if fwd_ch_id == self._raw_official_id and fwd_post_id == self._source_msg_id:
                return DiscoveryMethod.PUBLIC_FORWARD

        text = msg.text or getattr(msg, "message", None) or ""

        # 2. SOURCE_LINK
        if _contains_source_link(text, self._official_channel_url, self._source_msg_url):
            return DiscoveryMethod.SOURCE_LINK

        # 3 & 4. TEXT_COPY / NEAR_TEXT_COPY
        if text.strip() and self._normalized_source:
            try:
                normalized_candidate = normalize(text)
                score = similarity_score(self._normalized_source, normalized_candidate)
                if score == 1.0:
                    return DiscoveryMethod.TEXT_COPY
                if score >= self._threshold:
                    return DiscoveryMethod.NEAR_TEXT_COPY
            except Exception:
                pass

        return None
