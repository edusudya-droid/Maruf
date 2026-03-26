from sqlalchemy.ext.asyncio import AsyncSession

from domain.exceptions import AnalysisNotFoundError, ok, err
from infrastructure.repositories.analysis_repo import AnalysisRepo
from infrastructure.repositories.detected_post_repo import DetectedPostRepo
from infrastructure.repositories.post_repo import PostRepo


async def get_report(analysis_run_id: int, session: AsyncSession) -> dict:
    analysis_repo = AnalysisRepo(session)
    run = await analysis_repo.get_by_id(analysis_run_id)
    if not run:
        return err(AnalysisNotFoundError())

    post_repo = PostRepo(session)
    post = await post_repo.get_by_id(run.source_post_id)

    return ok(data={
        "post_url": post.post_url if post else "",
        "source_views": run.source_views,
        "counted_posts_count": run.counted_posts_count,
        "confirmed_secondary_views": run.confirmed_secondary_views,
        "total_confirmed_reach": run.total_confirmed_reach,
        "skipped_posts_count": run.skipped_posts_count,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "status": run.status,
        "notes": run.notes or "",
    })


async def get_detailed_report(analysis_run_id: int, session: AsyncSession) -> dict:
    analysis_repo = AnalysisRepo(session)
    run = await analysis_repo.get_by_id(analysis_run_id)
    if not run:
        return err(AnalysisNotFoundError())

    detected_repo = DetectedPostRepo(session)
    detected = await detected_repo.list_for_run(analysis_run_id)

    post_repo = PostRepo(session)
    post = await post_repo.get_by_id(run.source_post_id)

    return ok(data={
        "report": {
            "post_url": post.post_url if post else "",
            "source_views": run.source_views,
            "counted_posts_count": run.counted_posts_count,
            "confirmed_secondary_views": run.confirmed_secondary_views,
            "total_confirmed_reach": run.total_confirmed_reach,
            "skipped_posts_count": run.skipped_posts_count,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "status": run.status,
        },
        "detected_posts": [
            {
                "status": dp.status,
                "post_url": dp.post_url,
                "views_count": dp.views_count,
                "confirmation_type": dp.confirmation_type,
                "skip_reason": dp.skip_reason,
                "text_similarity_score": float(dp.text_similarity_score)
                if dp.text_similarity_score else None,
                "external_channel_name": dp.external_channel_name,
                "discovery_method": dp.discovery_method or "",
            }
            for dp in detected
        ],
    })


async def list_history(session: AsyncSession, limit: int = 50) -> dict:
    analysis_repo = AnalysisRepo(session)
    runs = await analysis_repo.list_all(limit=limit)
    post_repo = PostRepo(session)

    result = []
    for run in runs:
        post = await post_repo.get_by_id(run.source_post_id)
        result.append({
            "id": run.id,
            "post_url": post.post_url if post else "",
            "status": run.status,
            "started_at": run.started_at.isoformat(),
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "total_confirmed_reach": run.total_confirmed_reach,
        })
    return ok(data=result)
