"""Matnni normalizatsiya qilish."""
from loguru import logger


def detect_language(text: str) -> str:
    """Matn tilini aniqlash."""
    try:
        from langdetect import detect
        lang = detect(text[:500])
        if lang in ["uz", "ru", "en"]:
            return lang
        return "uz"
    except Exception:
        return "uz"


def normalize_text(text: str) -> str:
    """Tahlil uchun matnni normalizatsiya (lowercase)."""
    return text.lower().strip()
