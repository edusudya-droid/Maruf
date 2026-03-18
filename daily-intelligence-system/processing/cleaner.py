"""Matnni tozalash moduli."""
import re
import unicodedata
from bs4 import BeautifulSoup


def clean_text(text: str) -> str:
    """HTML teglarini, maxsus belgilarni olib, matnni tozalash."""
    if not text:
        return ""

    # HTML teglarini olib tashlash
    soup = BeautifulSoup(text, "lxml")
    text = soup.get_text(separator=" ")

    # Unicode normalizatsiya
    text = unicodedata.normalize("NFKC", text)

    # Ko'p bo'sh joylarni va yangi qatorlarni birlashtirish
    text = re.sub(r"\s+", " ", text)

    # Maxsus belgilarni tozalash (lekin punktuatsiyani saqlash)
    text = re.sub(r"[^\w\s\.,!?;:'\"\-\(\)\[\]«»""''–—]", " ", text, flags=re.UNICODE)

    return text.strip()


def is_valid_content(text: str, min_length: int = 50) -> bool:
    """Matn minimal uzunlik talabini qanoatlantiradimi?"""
    cleaned = clean_text(text)
    return len(cleaned) >= min_length
