"""
Analysis worker — 9-bosqich algoritm.

BOSQICH 1:  Manba postni olish
BOSQICH 2:  analysis_run yaratish → PENDING → RUNNING
BOSQICH 3:  Nomzodlarni yig'ish (4 usul)
BOSQICH 4:  Matn normalizatsiyasi
BOSQICH 5:  Mavjudlikni tekshirish
BOSQICH 6:  Tasdiqlash turini belgilash
BOSQICH 7:  Similarity hisoblash
BOSQICH 8:  Deduplikatsiya
BOSQICH 9:  Natijani hisoblash va yozish
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings as app_settings
from domain.algorithms.confirmation_classifier import classify
from domain.algorithms.deduplicator import Deduplicator
from domain.algorithms.text_comparator import similarity_score
from domain.algorithms.text_normalizer import normalize
from domain.enums import ConfirmationType, DetectedPostStatus
from domain.exceptions import (
    AppError,
    EmptyCandidateTextError,
    EmptySourceTextError,
    LowSimilarityError,
)
from infrastructure.database.connection import AsyncSessionLocal
from infrastructure.repositories.analysis_repo import AnalysisRepo
from infrastructure.repositories.detected_post_repo import DetectedPostRepo
from infrastructure.repositories.log_repo import AuditLogRepo, ErrorLogRepo
from infrastructure.repositories.post_repo import PostRepo
from infrastructure.repositories.settings_repo import SettingsRepo
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="workers.analysis_worker.run_analysis", bind=True, max_retries=0)
def run_analysis(self, analysis_run_id: int) -> None:
    """Celery task entry point — runs the async analysis in a new event loop."""
    asyncio.run(_run_analysis_async(analysis_run_id))


async def _run_analysis_async(analysis_run_id: int) -> None:
    async with AsyncSessionLocal() as session:
        await _execute(analysis_run_id, session)


async def _execute(analysis_run_id: int, session: AsyncSession) -> None:  # noqa: C901
    analysis_repo = AnalysisRepo(session)
    post_repo = PostRepo(session)
    detected_repo = DetectedPostRepo(session)
    error_repo = ErrorLogRepo(session)
    settings_repo = SettingsRepo(session)
    audit_repo = AuditLogRepo(session)

    # Load dynamic settings
    similarity_threshold = float(
        await settings_repo.get_value(
            "near_full_similarity_threshold",
            str(app_settings.similarity_threshold),
        )
    )
    retry_limit = int(
        await settings_repo.get_value(
            "unavailable_retry_limit",
            str(app_settings.retry_limit),
        )
    )

    # BOSQICH 2: PENDING → RUNNING
    run = await analysis_repo.get_by_id(analysis_run_id)
    if not run:
        logger.error("AnalysisRun %d topilmadi", analysis_run_id)
        return
    await analysis_repo.update_status(analysis_run_id, "RUNNING")
    await session.commit()

    # BOSQICH 1: Manba postni olish
    source_post = await post_repo.get_by_id(run.source_post_id)
    if not source_post:
        await _fail(analysis_repo, error_repo, session, analysis_run_id, "POST_NOT_FOUND",
                    "Manba post topilmadi")
        return

    source_views = source_post.views_count or 0

    try:
        normalized_source = normalize(source_post.post_text or "")
    except AppError:
        normalized_source = ""

    dedup = Deduplicator()

    # BOSQICH 3: Nomzodlarni yig'ish
    # NOTE: Real implementation requires Telethon/Telegram client for full search.
    # Here we implement the framework; actual forward/search calls are stubbed
    # and should be replaced with real Telegram client calls in production.
    candidates = await _collect_candidates(
        source_post=source_post,
        session=session,
    )

    counted_views = 0
    counted_count = 0
    skipped_count = 0

    for candidate in candidates:
        try:
            result = await _process_candidate(
                candidate=candidate,
                analysis_run_id=analysis_run_id,
                source_post_id=source_post.id,
                normalized_source=normalized_source,
                similarity_threshold=similarity_threshold,
                retry_limit=retry_limit,
                dedup=dedup,
                detected_repo=detected_repo,
                error_repo=error_repo,
                session=session,
            )
            if result == "COUNTED":
                counted_views += candidate.get("views_count", 0) or 0
                counted_count += 1
            else:
                skipped_count += 1
        except Exception as exc:
            logger.exception("Candidate xatoligi: %s", exc)
            skipped_count += 1
            await error_repo.create(
                error_code="UNEXPECTED_ERROR",
                error_message=str(exc),
                analysis_run_id=analysis_run_id,
            )

    # BOSQICH 9: Natijani hisoblash
    total_reach = source_views + counted_views

    if skipped_count == 0:
        final_status = "COMPLETED"
    elif counted_count == 0 and skipped_count > 0 and len(candidates) == 0:
        final_status = "COMPLETED"
    else:
        final_status = "COMPLETED_WITH_SKIPS" if skipped_count > 0 else "COMPLETED"

    await analysis_repo.update_results(
        run_id=analysis_run_id,
        status=final_status,
        source_views=source_views,
        confirmed_secondary_views=counted_views,
        total_confirmed_reach=total_reach,
        counted_posts_count=counted_count,
        skipped_posts_count=skipped_count,
    )
    await audit_repo.create(
        action_type="ANALYSIS_COMPLETED",
        user_id=run.started_by_user_id,
        object_type="AnalysisRun",
        object_id=str(analysis_run_id),
        details=f"status={final_status}, reach={total_reach}",
    )
    await session.commit()
    logger.info("AnalysisRun %d tugadi: %s, reach=%d", analysis_run_id, final_status, total_reach)


async def _process_candidate(  # noqa: C901
    candidate: Dict[str, Any],
    analysis_run_id: int,
    source_post_id: int,
    normalized_source: str,
    similarity_threshold: float,
    retry_limit: int,
    dedup: Deduplicator,
    detected_repo: DetectedPostRepo,
    error_repo: ErrorLogRepo,
    session: AsyncSession,
) -> str:
    """Process one candidate. Returns 'COUNTED' or 'SKIPPED_*'."""

    post_url = candidate.get("post_url")
    channel_id = candidate.get("channel_id")
    message_id = candidate.get("message_id")
    candidate_text = candidate.get("text")
    views_count = candidate.get("views_count")
    channel_name = candidate.get("channel_name")
    is_forward = candidate.get("is_forward", False)
    has_source_link = candidate.get("has_source_link", False)
    published_at = candidate.get("published_at")

    # BOSQICH 8: Deduplikatsiya
    if dedup.is_duplicate(
        post_url=post_url,
        channel_id=channel_id,
        message_id=message_id,
        text=candidate_text,
    ):
        await detected_repo.create(
            analysis_run_id=analysis_run_id,
            source_post_id=source_post_id,
            status=DetectedPostStatus.SKIPPED_DUPLICATE.value,
            external_channel_name=channel_name,
            external_channel_id=channel_id,
            telegram_message_id=message_id,
            post_url=post_url,
            views_count=views_count,
            skip_reason="SKIPPED_DUPLICATE",
            published_at=published_at,
        )
        await session.flush()
        return "SKIPPED_DUPLICATE"

    # BOSQICH 5: Mavjudlikni tekshirish
    unavailable = candidate.get("unavailable", False)
    if unavailable:
        retry_count = candidate.get("retry_count", 0)
        if retry_count >= retry_limit:
            await detected_repo.create(
                analysis_run_id=analysis_run_id,
                source_post_id=source_post_id,
                status=DetectedPostStatus.SKIPPED_UNAVAILABLE.value,
                external_channel_name=channel_name,
                external_channel_id=channel_id,
                telegram_message_id=message_id,
                post_url=post_url,
                skip_reason="Kanal yopiq yoki post o'chirilgan",
                published_at=published_at,
            )
            await session.flush()
            return "SKIPPED_UNAVAILABLE"

    # No views
    if views_count is None or views_count == 0:
        await detected_repo.create(
            analysis_run_id=analysis_run_id,
            source_post_id=source_post_id,
            status=DetectedPostStatus.SKIPPED_NO_VIEWS.value,
            external_channel_name=channel_name,
            external_channel_id=channel_id,
            telegram_message_id=message_id,
            post_url=post_url,
            views_count=views_count,
            skip_reason="Ko'rishlar ma'lumoti yo'q",
            published_at=published_at,
        )
        await session.flush()
        return "SKIPPED_NO_VIEWS"

    # BOSQICH 4 & 7: Matn normalizatsiyasi va similarity
    score: Optional[float] = None
    is_full_copy_flag = False

    if not is_forward and not has_source_link and candidate_text and normalized_source:
        try:
            normalized_candidate = normalize(candidate_text)
            score = similarity_score(normalized_source, normalized_candidate)
            is_full_copy_flag = score == 1.0
        except (EmptySourceTextError, EmptyCandidateTextError):
            score = None
        except AppError:
            score = None

    # BOSQICH 6: Tasdiqlash turini belgilash
    confirmation = classify(
        is_forward=is_forward,
        has_source_link=has_source_link,
        is_full_copy=is_full_copy_flag,
        similarity_score=score,
        threshold=similarity_threshold,
    )

    if confirmation is None:
        # Low similarity or unconfirmed
        status = (
            DetectedPostStatus.SKIPPED_LOW_SIMILARITY.value
            if score is not None and score < similarity_threshold
            else DetectedPostStatus.SKIPPED_UNCONFIRMED.value
        )
        await detected_repo.create(
            analysis_run_id=analysis_run_id,
            source_post_id=source_post_id,
            status=status,
            external_channel_name=channel_name,
            external_channel_id=channel_id,
            telegram_message_id=message_id,
            post_url=post_url,
            post_text=candidate_text,
            views_count=views_count,
            text_similarity_score=score,
            skip_reason=status,
            published_at=published_at,
        )
        await session.flush()
        return status

    # COUNTED
    dedup.register(
        post_url=post_url,
        channel_id=channel_id,
        message_id=message_id,
        text=candidate_text,
    )
    await detected_repo.create(
        analysis_run_id=analysis_run_id,
        source_post_id=source_post_id,
        status=DetectedPostStatus.COUNTED.value,
        external_channel_name=channel_name,
        external_channel_id=channel_id,
        telegram_message_id=message_id,
        post_url=post_url,
        post_text=candidate_text,
        views_count=views_count,
        confirmation_type=confirmation.value,
        text_similarity_score=score,
        published_at=published_at,
    )
    await session.flush()
    return "COUNTED"


async def _collect_candidates(source_post, session: AsyncSession) -> List[Dict[str, Any]]:
    """
    Collect candidate posts through 4 methods (priority order):
    1. Forwards/reposts via Bot API
    2. Posts containing source link
    3. Full text copies
    4. Near-full text copies

    NOTE: Full implementation requires Telegram client (Telethon/Pyrogram).
    This returns an empty list in the base implementation.
    Replace this function with real Telegram search calls in production.
    """
    return []


async def _fail(
    analysis_repo: AnalysisRepo,
    error_repo: ErrorLogRepo,
    session: AsyncSession,
    run_id: int,
    code: str,
    message: str,
) -> None:
    await analysis_repo.update_status(run_id, "FAILED")
    await error_repo.create(
        error_code=code,
        error_message=message,
        analysis_run_id=run_id,
    )
    await session.commit()
