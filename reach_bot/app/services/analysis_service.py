from sqlalchemy.ext.asyncio import AsyncSession

from config import settings as app_settings
from domain.exceptions import (
    AnalysisAlreadyRunningError,
    DailyLimitReachedError,
    PostNotFoundError,
    QueueError,
    ok,
    err,
)
from infrastructure.repositories.analysis_repo import AnalysisRepo
from infrastructure.repositories.post_repo import PostRepo


async def start_analysis(
    source_post_id: int,
    user_id: int,
    session: AsyncSession,
) -> dict:
    """
    Validate constraints and enqueue analysis task.
    Returns the analysis_run_id on success.
    """
    post_repo = PostRepo(session)
    post = await post_repo.get_by_id(source_post_id)
    if not post:
        return err(PostNotFoundError())

    analysis_repo = AnalysisRepo(session)

    # Check for already-running analysis on this post
    running = await analysis_repo.get_running_for_post(source_post_id)
    if running:
        return err(AnalysisAlreadyRunningError())

    # Daily limit check
    today_count = await analysis_repo.count_today()
    max_daily = app_settings.max_daily_analyses
    if today_count >= max_daily:
        return err(DailyLimitReachedError(f"Kunlik limit ({max_daily}) to'ldi"))

    # Create run record
    run = await analysis_repo.create(
        source_post_id=source_post_id,
        started_by_user_id=user_id,
    )
    await session.commit()

    # Enqueue Celery task
    try:
        from workers.analysis_worker import run_analysis
        run_analysis.delay(run.id)
    except Exception as exc:
        return err(QueueError(f"Navbat xatosi: {exc}"))

    return ok(data={"analysis_run_id": run.id})


async def get_analysis_run(run_id: int, session: AsyncSession) -> dict:
    repo = AnalysisRepo(session)
    run = await repo.get_by_id(run_id)
    if not run:
        from domain.exceptions import AnalysisNotFoundError
        return err(AnalysisNotFoundError())
    return ok(data=run)


async def get_latest_run_for_post(source_post_id: int, session: AsyncSession) -> dict:
    repo = AnalysisRepo(session)
    runs = await repo.list_for_post(source_post_id)
    if not runs:
        from domain.exceptions import AnalysisNotFoundError
        return err(AnalysisNotFoundError())
    return ok(data=runs[0])
