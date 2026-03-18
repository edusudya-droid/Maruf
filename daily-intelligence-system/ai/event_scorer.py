"""Voqea uchun Event Score hisoblash."""
from datetime import datetime
from typing import Optional
from database.models import Event, Article, ImpactLevel


def calculate_event_score(
    event: Event,
    articles: list[Article],
    user_topics: Optional[list[str]] = None,
) -> tuple[float, str]:
    """
    Event Score hisoblash (0-100).
    Returns: (score, priority)
    """
    # 1. Source Trust Score (0-30 ball)
    tier_weights = {1: 30, 2: 20, 3: 12, 4: 6, 5: 2}
    if articles:
        trust_scores = []
        for a in articles:
            if hasattr(a, "source") and a.source:
                tier = getattr(a.source, "tier", 3)
                trust_scores.append(tier_weights.get(tier, 6))
            else:
                trust_scores.append(6)
        source_trust = sum(trust_scores) / len(trust_scores)
    else:
        source_trust = 6.0

    # 2. Source Count Score (0-25 ball)
    count = len(articles)
    if count >= 10:
        source_count = 25
    elif count >= 5:
        source_count = 18
    elif count >= 3:
        source_count = 12
    else:
        source_count = 5

    # 3. Impact Score (0-20 ball)
    impact_map = {
        ImpactLevel.international: 20,
        ImpactLevel.national: 15,
        ImpactLevel.regional: 8,
        ImpactLevel.local: 3,
    }
    impact = impact_map.get(event.impact_level, 10)

    # 4. Novelty Score (0-15 ball)
    hours_old = (datetime.utcnow() - event.first_seen_at).total_seconds() / 3600
    if hours_old < 2:
        novelty = 15
    elif hours_old < 6:
        novelty = 10
    else:
        novelty = 5

    # 5. Topic Relevance Score (0-10 ball)
    relevance = 5
    if user_topics and event.category:
        if event.category.value in user_topics:
            relevance = 10

    total = source_trust + source_count + impact + novelty + relevance

    # Priority aniqlash
    if total >= 70:
        priority = "high"
    elif total >= 40:
        priority = "medium"
    else:
        priority = "low"

    return round(total, 2), priority
