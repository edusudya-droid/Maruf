"""Statistika API."""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.api.dependencies import get_db, verify_admin
from database.models import Source, Article, Event, User, Brief

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview")
async def overview_stats(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    sources_count = await db.scalar(select(func.count(Source.id)))
    articles_count = await db.scalar(select(func.count(Article.id)))
    events_count = await db.scalar(select(func.count(Event.id)))
    users_count = await db.scalar(select(func.count(User.id)))
    briefs_count = await db.scalar(select(func.count(Brief.id)))

    active_sources = await db.scalar(
        select(func.count(Source.id)).where(Source.is_active == True)
    )
    active_users = await db.scalar(
        select(func.count(User.id)).where(User.is_active == True)
    )

    return {
        "sources": {"total": sources_count, "active": active_sources},
        "articles": {"total": articles_count},
        "events": {"total": events_count},
        "users": {"total": users_count, "active": active_users},
        "briefs": {"total": briefs_count},
    }


@router.get("/sources")
async def source_stats(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    result = await db.execute(
        select(
            Source.tier,
            func.count(Source.id).label("count"),
            func.avg(Source.final_score).label("avg_score"),
        )
        .where(Source.is_active == True)
        .group_by(Source.tier)
        .order_by(Source.tier)
    )
    return [
        {"tier": row.tier, "count": row.count, "avg_score": round(row.avg_score or 0, 2)}
        for row in result.fetchall()
    ]


@router.get("/events")
async def event_stats(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    result = await db.execute(
        select(
            Event.priority,
            func.count(Event.id).label("count"),
            func.avg(Event.event_score).label("avg_score"),
        )
        .group_by(Event.priority)
    )
    return [
        {"priority": row.priority.value, "count": row.count, "avg_score": round(row.avg_score or 0, 2)}
        for row in result.fetchall()
    ]


@router.get("/users")
async def user_stats(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    by_role = await db.execute(
        select(User.user_role, func.count(User.id).label("count")).group_by(User.user_role)
    )
    by_format = await db.execute(
        select(User.format, func.count(User.id).label("count")).group_by(User.format)
    )
    return {
        "by_role": [{"role": r.user_role.value, "count": r.count} for r in by_role.fetchall()],
        "by_format": [{"format": r.format.value, "count": r.count} for r in by_format.fetchall()],
    }
