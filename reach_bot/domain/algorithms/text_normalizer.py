import re
from typing import Optional

from domain.exceptions import EmptyTextError, NormalizationError


def normalize(text: Optional[str]) -> str:
    """
    Normalize text for comparison:
    - lowercase
    - strip extra whitespace
    - unify links
    - normalize line breaks
    Raises EmptyTextError if input is empty/None.
    Raises NormalizationError on unexpected failure.
    """
    if not text or not text.strip():
        raise EmptyTextError()
    try:
        result = text.lower()
        # Normalize line breaks
        result = result.replace("\r\n", "\n").replace("\r", "\n")
        # Unify URLs: strip trailing slashes and query params for comparison
        result = re.sub(r"https?://\S+", lambda m: _normalize_url(m.group()), result)
        # Collapse multiple whitespace/newlines
        result = re.sub(r"[ \t]+", " ", result)
        result = re.sub(r"\n{3,}", "\n\n", result)
        result = result.strip()
        return result
    except EmptyTextError:
        raise
    except Exception as exc:
        raise NormalizationError(f"Normalizatsiya xatosi: {exc}") from exc


def _normalize_url(url: str) -> str:
    # Remove trailing punctuation that may have been captured
    url = url.rstrip(".,;:!?)")
    return url
