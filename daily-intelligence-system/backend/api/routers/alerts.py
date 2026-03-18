"""Ogohlantirishlar API."""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.api.dependencies import get_db, verify_admin
from database.models import Alert

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/")
async def list_alerts(
    alert_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    conditions = []
    if alert_type:
        conditions.append(Alert.alert_type == alert_type)

    from sqlalchemy import and_
    result = await db.execute(
        select(Alert)
        .where(and_(*conditions) if conditions else True)
        .order_by(Alert.created_at.desc())
        .limit(50)
    )
    alerts = result.scalars().all()
    return [
        {
            "id": a.id, "alert_type": a.alert_type.value,
            "title": a.title, "message": a.message,
            "sent_at": a.sent_at.isoformat() if a.sent_at else None,
            "recipient_count": a.recipient_count,
            "created_at": a.created_at.isoformat(),
        }
        for a in alerts
    ]
