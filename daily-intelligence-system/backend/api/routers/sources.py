"""Manbalar CRUD API."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from backend.api.dependencies import get_db, verify_admin
from database.models import Source, SourceType, SourceCategory

router = APIRouter(prefix="/sources", tags=["sources"])


class SourceCreate(BaseModel):
    name: str
    url: str
    rss_url: Optional[str] = None
    telegram_channel: Optional[str] = None
    source_type: SourceType
    category: SourceCategory
    tier: int = 3
    trust_score: float = 0.5
    priority: int = 5
    language: str = "uz"
    country: str = "UZ"


class SourceUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    tier: Optional[int] = None
    trust_score: Optional[float] = None
    priority: Optional[int] = None


@router.get("/")
async def list_sources(
    tier: Optional[int] = None,
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    conditions = []
    if tier is not None:
        conditions.append(Source.tier == tier)
    if category:
        conditions.append(Source.category == category)
    if is_active is not None:
        conditions.append(Source.is_active == is_active)

    result = await db.execute(
        select(Source).where(and_(*conditions) if conditions else True)
        .order_by(Source.tier, Source.priority.desc())
    )
    sources = result.scalars().all()
    return [_source_dict(s) for s in sources]


@router.post("/", status_code=201)
async def create_source(
    data: SourceCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    source = Source(**data.model_dump())
    db.add(source)
    await db.flush()
    return _source_dict(source)


@router.get("/{source_id}")
async def get_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return _source_dict(source)


@router.put("/{source_id}")
async def update_source(
    source_id: int,
    data: SourceUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(source, field, value)
    return _source_dict(source)


@router.delete("/{source_id}", status_code=204)
async def delete_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    await db.delete(source)


@router.post("/{source_id}/test")
async def test_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    from parser.source_manager import SourceManager
    manager = SourceManager()
    parser = manager._build_parser(source)
    if not parser:
        raise HTTPException(status_code=400, detail="Parser not available for this source type")

    articles = await parser.safe_fetch()
    return {"source": source.name, "articles_found": len(articles), "sample": articles[:2]}


@router.post("/{source_id}/rescore")
async def rescore_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    from source_intelligence.dynamic_scorer import _calculate_source_score, _save_score
    from datetime import date
    today = date.today()
    score_data = await _calculate_source_score(source, today)
    await _save_score(source, score_data, today)
    return {"source": source.name, **score_data}


def _source_dict(s: Source) -> dict:
    return {
        "id": s.id, "name": s.name, "url": s.url,
        "source_type": s.source_type.value, "category": s.category.value,
        "tier": s.tier, "trust_score": s.trust_score,
        "is_active": s.is_active, "final_score": s.final_score,
        "posts_per_day": s.posts_per_day, "language": s.language,
    }
