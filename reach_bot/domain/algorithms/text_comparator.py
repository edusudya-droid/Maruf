from typing import Optional

from rapidfuzz import fuzz

from domain.exceptions import EmptyCandidateTextError, EmptySourceTextError, TextCompareError


def similarity_score(source_text: Optional[str], candidate_text: Optional[str]) -> float:
    """
    Compute text similarity score in [0, 1] using rapidfuzz token_set_ratio.
    Raises EmptySourceTextError / EmptyCandidateTextError if either is empty.
    Raises TextCompareError on unexpected failure.
    """
    if not source_text or not source_text.strip():
        raise EmptySourceTextError()
    if not candidate_text or not candidate_text.strip():
        raise EmptyCandidateTextError()
    try:
        score = fuzz.token_set_ratio(source_text, candidate_text) / 100.0
        return round(score, 4)
    except Exception as exc:
        raise TextCompareError(f"Matn taqqoslash xatosi: {exc}") from exc


def is_full_copy(source_text: str, candidate_text: str) -> bool:
    """True if candidate is (near-)exact copy of source (score == 1.0)."""
    return similarity_score(source_text, candidate_text) == 1.0
