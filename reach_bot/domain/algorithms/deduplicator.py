import hashlib
from typing import Optional, Set


class Deduplicator:
    """
    In-memory deduplication within a single analysis run.
    Tracks: post URLs, (channel_id, message_id) pairs, text hashes.
    """

    def __init__(self):
        self._urls: Set[str] = set()
        self._msg_keys: Set[tuple] = set()
        self._text_hashes: Set[str] = set()

    def is_duplicate(
        self,
        post_url: Optional[str] = None,
        channel_id: Optional[int] = None,
        message_id: Optional[int] = None,
        text: Optional[str] = None,
    ) -> bool:
        if post_url and post_url in self._urls:
            return True
        if channel_id is not None and message_id is not None:
            if (channel_id, message_id) in self._msg_keys:
                return True
        if text:
            h = _hash(text)
            if h in self._text_hashes:
                return True
        return False

    def register(
        self,
        post_url: Optional[str] = None,
        channel_id: Optional[int] = None,
        message_id: Optional[int] = None,
        text: Optional[str] = None,
    ) -> None:
        if post_url:
            self._urls.add(post_url)
        if channel_id is not None and message_id is not None:
            self._msg_keys.add((channel_id, message_id))
        if text:
            self._text_hashes.add(_hash(text))


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
