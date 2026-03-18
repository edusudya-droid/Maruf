"""Maqolalar API."""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from backend.api.dependencies import get_db, verify_admin
from database.models import Article, ArticleCategory

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("/")
async def list_articles(
    source_id: Optional[int] = None,
    category: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    is_duplicate: Optional[bool] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    conditions = []
    if source_id:
        conditions.append(Article.source_id == source_id)
    if category:
        conditions.append(Article.category == category)
    if date_from:
        conditions.append(Article.published_at >= date_from)
    if date_to:
        conditions.append(Article.published_at <= date_to)
    if is_duplicate is not None:
        conditions.append(Article.is_duplicate == is_duplicate)

    result = await db.execute(
        select(Article)
        .where(and_(*conditions) if conditions else True)
        .order_by(Article.published_at.desc())
        .offset(offset).limit(limit)
    )
    articles = result.scalars().all()
    return [_article_dict(a) for a in articles]


@router.get("/{article_id}")
async def get_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return _article_dict(article)


@router.delete("/{article_id}", status_code=204)
async def delete_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_admin),
):
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    await db.delete(article)


def _article_dict(a: Article) -> dict:
    return {
        "id": a.id, "title": a.title, "url": a.url,
        "source_id": a.source_id,
        "category": a.category.value if a.category else None,
        "sentiment": a.sentiment.value if a.sentiment else None,
        "importance_score": a.importance_score,
        "is_duplicate": a.is_duplicate,
        "is_processed": a.is_processed,
        "published_at": a.published_at.isoformat(),
        "summary": a.summary,
    }
