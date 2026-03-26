from typing import Optional, Set


class Deduplicator:
    """
    In-memory deduplication within a single analysis run.

    Дедупликация ТОЛЬКО по техническим идентификаторам публикации:
      - post_url
      - (channel_id, message_id)

    Текст НЕ является критерием дедупликации.
    Одинаковый текст в разных каналах — это разные публикации,
    каждая из которых должна быть учтена отдельно.
    """

    def __init__(self):
        self._urls: Set[str] = set()
        self._msg_keys: Set[tuple] = set()

    def is_duplicate(
        self,
        post_url: Optional[str] = None,
        channel_id: Optional[int] = None,
        message_id: Optional[int] = None,
        text: Optional[str] = None,  # не используется, сохранён для совместимости сигнатуры
    ) -> bool:
        if post_url and post_url in self._urls:
            return True
        if channel_id is not None and message_id is not None:
            if (channel_id, message_id) in self._msg_keys:
                return True
        return False

    def register(
        self,
        post_url: Optional[str] = None,
        channel_id: Optional[int] = None,
        message_id: Optional[int] = None,
        text: Optional[str] = None,  # не используется, сохранён для совместимости сигнатуры
    ) -> None:
        if post_url:
            self._urls.add(post_url)
        if channel_id is not None and message_id is not None:
            self._msg_keys.add((channel_id, message_id))
