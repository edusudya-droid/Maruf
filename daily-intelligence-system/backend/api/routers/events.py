"""Voqealar API."""
from typing import Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.api.dependencies import get_db, verify_admin
from database.models import Event, EventPriority, ArticleCategory

router = APIRouter(prefix="/events", tags=["events"])


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    event_score: Optional[float] = None


@router.get("/")
async def list_events(
    priority: Optional[str] = None,
    category: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    is_hidden: Optional[bool] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    conditions = []
    if priority:
        conditions.append(Event.priority == priority)
    if category:
        conditions.append(Event.category == category)
    if date_from:
        conditions.append(Event.created_at >= date_from)
    if date_to:
        conditions.append(Event.created_at <= date_to)
    if is_hidden is not None:
        conditions.append(Event.is_hidden_event == is_hidden)

    result = await db.execute(
        select(Event)
        .where(and_(*conditions) if conditions else True)
        .order_by(Event.event_score.desc())
        .offset(offset).limit(limit)
    )
    events = result.scalars().all()
    return [_event_dict(e) for e in events]


@router.get("/{event_id}")
async def get_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return _event_dict(event)


@router.put("/{event_id}")
async def update_event(
    event_id: int,
    data: EventUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(event, field, value)
    return _event_dict(event)


@router.post("/detect")
async def run_event_detection(
    _: None = Depends(verify_admin),
):
    from ai.event_detector import detect_events
    count = await detect_events()
    return {"message": f"{count} events detected"}


def _event_dict(e: Event) -> dict:
    return {
        "id": e.id, "title": e.title, "description": e.description[:300],
        "category": e.category.value,
        "priority": e.priority.value,
        "event_score": e.event_score,
        "risk_score": e.risk_score,
        "source_count": e.source_count,
        "is_hidden_event": e.is_hidden_event,
        "impact_level": e.impact_level.value,
        "created_at": e.created_at.isoformat(),
    }
