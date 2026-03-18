"""Dynamic Source Scoring — manbalar reytingini avtomatik yangilash."""
from datetime import datetime, timedelta, date
from statistics import mean
from loguru import logger
from sqlalchemy import select, and_, func
from backend.core.database import AsyncSessionLocal
from database.models import Source, SourceScoreHistory, Article, Event, EventArticle


async def update_source_scores() -> None:
    """Barcha manba scorlarini hisoblash va yangilash."""
    today = date.today()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Source).where(Source.is_active == True)
        )
        sources = result.scalars().all()

    for source in sources:
        try:
            score_data = await _calculate_source_score(source, today)
            await _save_score(source, score_data, today)
            logger.debug(f"Score updated for {source.name}: {score_data['final_score']:.1f}")
        except Exception as e:
            logger.error(f"Score update failed for {source.name}: {e}")

    logger.info(f"Source scores updated for {len(sources)} sources")


async def _calculate_source_score(source: Source, today: date) -> dict:
    """Bitta manba uchun barcha balllarni hisoblash."""
    since_30d = datetime.utcnow() - timedelta(days=30)
    since_24h = datetime.utcnow() - timedelta(hours=24)

    async with AsyncSessionLocal() as session:
        # Bugungi maqolalar soni
        articles_result = await session.execute(
            select(func.count(Article.id)).where(
                and_(
                    Article.source_id == source.id,
                    Article.created_at >= since_24h,
                )
            )
        )
        articles_today = articles_result.scalar() or 0

        # Voqealarga qo'shilgan maqolalar soni (signal)
        events_result = await session.execute(
            select(func.count(EventArticle.article_id)).join(
                Article, EventArticle.article_id == Article.id
            ).where(
                and_(
                    Article.source_id == source.id,
                    Article.created_at >= since_24h,
                )
            )
        )
        in_events = events_result.scalar() or 0

    # Signal Score
    signal_score = min(in_events * 5, 30)

    # Accuracy Score (soddalashtirilgan: ishonch ballidan)
    accuracy_score = min(source.trust_score * 20, 20)

    # Speed Score (tier asosida)
    speed_map = {1: 10, 2: 7, 3: 5, 4: 3, 5: 1}
    speed_score = speed_map.get(source.tier, 3)

    # Noise Penalty
    noise_penalty = 0.0
    posts_per_day = source.posts_per_day or articles_today
    if posts_per_day > 50:
        noise_penalty += 10
    elif posts_per_day > 30:
        noise_penalty += 5
    if source.noise_level > 0.7:
        noise_penalty += 5

    # Joriy ball
    current_score = source.base_score + signal_score + accuracy_score + speed_score - noise_penalty
    current_score = max(0.0, min(100.0, current_score))

    # Tarixiy o'rtacha (30 kunlik)
    async with AsyncSessionLocal() as session:
        history_result = await session.execute(
            select(SourceScoreHistory.final_score).where(
                and_(
                    SourceScoreHistory.source_id == source.id,
                    SourceScoreHistory.score_date >= since_30d,
                )
            ).order_by(SourceScoreHistory.score_date.desc()).limit(30)
        )
        history_scores = [row[0] for row in history_result.fetchall()]

    historical_score = mean(history_scores) if history_scores else current_score

    # Yakuniy ball
    final_score = 0.6 * current_score + 0.4 * historical_score

    # Anti-manipulyatsiya
    if posts_per_day > 50:
        final_score = max(0, final_score - 10)

    # Tier yangilash
    if final_score >= 80:
        new_tier = 1
    elif final_score >= 60:
        new_tier = 2
    elif final_score >= 40:
        new_tier = 3
    elif final_score >= 20:
        new_tier = 4
    else:
        new_tier = 5

    # Anti-manipulyatsiya: posts_per_day > 50 bo'lsa tier bir pastga
    if posts_per_day > 50:
        new_tier = min(new_tier + 1, 5)

    return {
        "signal_score": round(signal_score, 2),
        "accuracy_score": round(accuracy_score, 2),
        "speed_score": round(speed_score, 2),
        "noise_penalty": round(noise_penalty, 2),
        "current_score": round(current_score, 2),
        "historical_score": round(historical_score, 2),
        "final_score": round(final_score, 2),
        "tier": new_tier,
    }


async def _save_score(source: Source, score_data: dict, today: date) -> None:
    """Score natijalarini bazaga saqlash."""
    async with AsyncSessionLocal() as session:
        # source_score_history ga qo'shish yoki yangilash
        existing = await session.execute(
            select(SourceScoreHistory).where(
                and_(
                    SourceScoreHistory.source_id == source.id,
                    SourceScoreHistory.score_date == today,
                )
            )
        )
        history = existing.scalar_one_or_none()

        if history:
            history.signal_score = score_data["signal_score"]
            history.accuracy_score = score_data["accuracy_score"]
            history.speed_score = score_data["speed_score"]
            history.noise_penalty = score_data["noise_penalty"]
            history.final_score = score_data["final_score"]
            history.tier = score_data["tier"]
        else:
            history = SourceScoreHistory(
                source_id=source.id,
                score_date=today,
                **{k: v for k, v in score_data.items() if k != "current_score" and k != "historical_score"},
            )
            session.add(history)

        # source jadvalini yangilash
        db_source = await session.get(Source, source.id)
        if db_source:
            db_source.current_score = score_data["current_score"]
            db_source.historical_score = score_data["historical_score"]
            db_source.final_score = score_data["final_score"]
            db_source.signal_score = score_data["signal_score"]
            db_source.accuracy_score = score_data["accuracy_score"]
            db_source.speed_score = score_data["speed_score"]
            db_source.noise_penalty = score_data["noise_penalty"]
            db_source.tier = score_data["tier"]
            db_source.last_score_update = datetime.utcnow()

        await session.commit()
