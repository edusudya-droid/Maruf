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

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

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
    # Create a fresh engine per task to avoid "Future attached to different loop" error
    engine = create_async_engine(app_settings.database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_factory() as session:
            await _execute(analysis_run_id, session)
    finally:
        await engine.dispose()


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

    try:
        normalized_source = normalize(source_post.post_text or "")
    except AppError:
        normalized_source = ""

    dedup = Deduplicator()

    # BOSQICH 3: Nomzodlarni yig'ish + source post views yangilash
    # _collect_candidates Telethon orqali haqiqiy views ni oladi va
    # source_post.views_count ni yangilaydi — shuning uchun KEYIN o'qiymiz.
    candidates = await _collect_candidates(
        source_post=source_post,
        session=session,
    )

    # views _collect_candidates tomonidan yangilangan bo'lishi mumkin
    source_views = source_post.views_count or 0

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
    Nomzod postlarni yig'adi:
    1. Rasmiy kanalda manba postning haqiqiy views sonini Telethon orqali oladi
       va source_post.views_count ni yangilaydi (Bot API buni qaytarmaydi).
    2. Bot a'zo bo'lgan barcha kanallarda berilgan postning forwardlarini qidiradi.

    Agar Telethon sozlanmagan bo'lsa — bo'sh list qaytaradi.
    """
    from infrastructure.telegram.client import is_telethon_configured, make_telethon_client
    from infrastructure.telegram.repost_finder import find_reposts, get_message_views

    if not is_telethon_configured():
        logger.warning(
            "Telethon sozlanmagan (TELEGRAM_API_ID / TELEGRAM_API_HASH / TELETHON_SESSION) "
            "— candidates bo'sh qaytarildi."
        )
        return []

    # Rasmiy kanal ma'lumotlarini yuklash
    from sqlalchemy import select as sa_select
    from infrastructure.database.models import OfficialChannel

    result = await session.execute(
        sa_select(OfficialChannel).where(
            OfficialChannel.id == source_post.official_channel_id
        )
    )
    official_channel = result.scalar_one_or_none()
    if not official_channel:
        logger.error(
            "OfficialChannel topilmadi: id=%s", source_post.official_channel_id
        )
        return []

    channel_bot_api_id = official_channel.telegram_channel_id

    client = make_telethon_client()
    await client.connect()

    try:
        if not await client.is_user_authorized():
            logger.error(
                "Telethon session yaroqsiz. "
                "Qayta autentifikatsiya: "
                "docker-compose run --rm bot python -m infrastructure.telegram.generate_session"
            )
            return []

        # 1. Haqiqiy views sonini olish va yangilash
        views = await get_message_views(
            client, channel_bot_api_id, source_post.telegram_message_id
        )
        if views is not None and views > (source_post.views_count or 0):
            source_post.views_count = views
            await session.flush()
            logger.info(
                "Source post views yangilandi: message_id=%s, views=%s",
                source_post.telegram_message_id, views,
            )

        # 2. Repostlarni qidirish
        candidates = await find_reposts(
            client=client,
            official_channel_bot_api_id=channel_bot_api_id,
            source_message_id=source_post.telegram_message_id,
        )
        return candidates

    finally:
        await client.disconnect()


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
