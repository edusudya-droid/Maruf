"""Briflar API."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.api.dependencies import get_db, verify_admin
from database.models import Brief, BriefType

router = APIRouter(prefix="/briefs", tags=["briefs"])


@router.get("/")
async def list_briefs(
    brief_type: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    conditions = []
    if brief_type:
        conditions.append(Brief.brief_type == brief_type)

    from sqlalchemy import and_
    result = await db.execute(
        select(Brief)
        .where(and_(*conditions) if conditions else True)
        .order_by(Brief.created_at.desc())
        .limit(limit)
    )
    briefs = result.scalars().all()
    return [_brief_dict(b) for b in briefs]


@router.get("/{brief_id}")
async def get_brief(
    brief_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    brief = await db.get(Brief, brief_id)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")
    return _brief_dict(brief, full=True)


@router.post("/generate")
async def generate_brief_endpoint(
    brief_type: str = "morning",
    _: None = Depends(verify_admin),
):
    from ai.brief_generator import generate_brief
    try:
        brief_type_enum = BriefType(brief_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid brief type: {brief_type}")

    brief = await generate_brief(brief_type_enum)
    if not brief:
        raise HTTPException(status_code=500, detail="Brief generation failed")
    return _brief_dict(brief)


@router.post("/{brief_id}/send")
async def send_brief_endpoint(
    brief_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    brief = await db.get(Brief, brief_id)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")

    from notifications.telegram_sender import send_brief_to_all_users
    count = await send_brief_to_all_users(brief)
    return {"message": f"Brief sent to {count} users"}


def _brief_dict(b: Brief, full: bool = False) -> dict:
    result = {
        "id": b.id,
        "brief_type": b.brief_type.value,
        "title": b.title,
        "generated_at": b.generated_at.isoformat(),
        "sent_at": b.sent_at.isoformat() if b.sent_at else None,
        "recipient_count": b.recipient_count,
    }
    if full:
        result["content"] = b.content
    return result
