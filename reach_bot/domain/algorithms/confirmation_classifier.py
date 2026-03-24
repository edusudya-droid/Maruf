from typing import Optional

from domain.enums import ConfirmationType


def classify(
    is_forward: bool,
    has_source_link: bool,
    is_full_copy: bool,
    similarity_score: Optional[float],
    threshold: float = 0.90,
) -> Optional[ConfirmationType]:
    """
    Determine confirmation type by priority:
    1. FORWARD_CONFIRMED
    2. SOURCE_LINK_CONFIRMED
    3. FULL_TEXT_COPY_CONFIRMED
    4. NEAR_FULL_TEXT_COPY_CONFIRMED (score >= threshold)
    Returns None if none of the conditions match.
    """
    if is_forward:
        return ConfirmationType.FORWARD_CONFIRMED
    if has_source_link:
        return ConfirmationType.SOURCE_LINK_CONFIRMED
    if is_full_copy:
        return ConfirmationType.FULL_TEXT_COPY_CONFIRMED
    if similarity_score is not None and similarity_score >= threshold:
        return ConfirmationType.NEAR_FULL_TEXT_COPY_CONFIRMED
    return None
