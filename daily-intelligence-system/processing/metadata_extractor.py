"""Maqoladan metadata ajratish."""
from datetime import datetime
from typing import Optional
from processing.normalizer import detect_language


def extract_metadata(article_data: dict) -> dict:
    """Maqola dict'idan metadata ajratish va to'ldirish."""
    metadata = {}

    # Til aniqlash
    text = article_data.get("content", "") or article_data.get("title", "")
    if text and not article_data.get("language"):
        metadata["language"] = detect_language(text)

    # published_at bo'lmasa hozirgi vaqtni qo'yish
    if not article_data.get("published_at"):
        metadata["published_at"] = datetime.utcnow()

    return metadata
