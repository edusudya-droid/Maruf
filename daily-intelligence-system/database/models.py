import enum
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import (
    Integer, String, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, Enum as SAEnum, BigInteger, Date, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from backend.core.database import Base


# ─── Enums ───────────────────────────────────────────────────────────────────

class SourceType(str, enum.Enum):
    rss = "rss"
    html = "html"
    telegram = "telegram"
    api = "api"


class SourceCategory(str, enum.Enum):
    news = "news"
    gov = "gov"
    analytics = "analytics"
    legal = "legal"
    economic = "economic"
    corporate = "corporate"
    international = "international"
    regional = "regional"


class ArticleCategory(str, enum.Enum):
    economics = "economics"
    law = "law"
    business = "business"
    international = "international"
    risk = "risk"
    technology = "technology"
    agriculture = "agriculture"
    infrastructure = "infrastructure"


class Sentiment(str, enum.Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class EventPriority(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class ImpactLevel(str, enum.Enum):
    local = "local"
    regional = "regional"
    national = "national"
    international = "international"


class BriefType(str, enum.Enum):
    morning = "morning"
    midday = "midday"
    evening = "evening"
    thematic = "thematic"
    weekly = "weekly"
    risk_report = "risk_report"
    strategic = "strategic"


class UserRole(str, enum.Enum):
    entrepreneur = "entrepreneur"
    analyst = "analyst"
    lawyer = "lawyer"
    investor = "investor"
    official = "official"
    other = "other"


class UserLanguage(str, enum.Enum):
    uz = "uz"
    ru = "ru"
    en = "en"


class UserFormat(str, enum.Enum):
    quick = "quick"
    standard = "standard"
    extended = "extended"


class ArticleRole(str, enum.Enum):
    primary = "primary"
    supporting = "supporting"
    analytical = "analytical"


class AlertType(str, enum.Enum):
    urgent = "urgent"
    risk = "risk"
    opportunity = "opportunity"


# ─── Models ──────────────────────────────────────────────────────────────────

class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    rss_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    telegram_channel: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_type: Mapped[SourceType] = mapped_column(SAEnum(SourceType), nullable=False)
    category: Mapped[SourceCategory] = mapped_column(SAEnum(SourceCategory), nullable=False)
    tier: Mapped[int] = mapped_column(Integer, default=3)
    trust_score: Mapped[float] = mapped_column(Float, default=0.5)
    priority: Mapped[int] = mapped_column(Integer, default=5)
    language: Mapped[str] = mapped_column(String(5), default="uz")
    country: Mapped[str] = mapped_column(String(5), default="UZ")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    noise_level: Mapped[float] = mapped_column(Float, default=0.3)
    posts_per_day: Mapped[float] = mapped_column(Float, default=10.0)
    avg_views: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    subscribers: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Dynamic Scoring
    base_score: Mapped[float] = mapped_column(Float, default=50.0)
    current_score: Mapped[float] = mapped_column(Float, default=50.0)
    historical_score: Mapped[float] = mapped_column(Float, default=50.0)
    final_score: Mapped[float] = mapped_column(Float, default=50.0)
    signal_score: Mapped[float] = mapped_column(Float, default=0.0)
    accuracy_score: Mapped[float] = mapped_column(Float, default=0.0)
    speed_score: Mapped[float] = mapped_column(Float, default=0.0)
    noise_penalty: Mapped[float] = mapped_column(Float, default=0.0)
    last_score_update: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    articles: Mapped[list["Article"]] = relationship("Article", back_populates="source")
    score_history: Mapped[list["SourceScoreHistory"]] = relationship(
        "SourceScoreHistory", back_populates="source"
    )


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("sources.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    language: Mapped[str] = mapped_column(String(5), default="uz")
    category: Mapped[Optional[ArticleCategory]] = mapped_column(SAEnum(ArticleCategory), nullable=True)
    sentiment: Mapped[Optional[Sentiment]] = mapped_column(SAEnum(Sentiment), nullable=True)
    importance_score: Mapped[float] = mapped_column(Float, default=0.0)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_of: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("articles.id"), nullable=True)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    entities: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    source: Mapped["Source"] = relationship("Source", back_populates="articles")
    event_articles: Mapped[list["EventArticle"]] = relationship("EventArticle", back_populates="article")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[ArticleCategory] = mapped_column(SAEnum(ArticleCategory), nullable=False)
    priority: Mapped[EventPriority] = mapped_column(SAEnum(EventPriority), default=EventPriority.medium)
    event_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    strategic_value: Mapped[float] = mapped_column(Float, default=0.0)
    impact_level: Mapped[ImpactLevel] = mapped_column(SAEnum(ImpactLevel), default=ImpactLevel.national)
    source_count: Mapped[int] = mapped_column(Integer, default=1)
    is_hidden_event: Mapped[bool] = mapped_column(Boolean, default=False)
    hidden_event_score: Mapped[float] = mapped_column(Float, default=0.0)
    geography: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    entities: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    timeline: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    event_articles: Mapped[list["EventArticle"]] = relationship("EventArticle", back_populates="event")
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="event")


class EventArticle(Base):
    __tablename__ = "event_articles"

    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("events.id"), primary_key=True)
    article_id: Mapped[int] = mapped_column(Integer, ForeignKey("articles.id"), primary_key=True)
    role: Mapped[ArticleRole] = mapped_column(SAEnum(ArticleRole), default=ArticleRole.supporting)
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    event: Mapped["Event"] = relationship("Event", back_populates="event_articles")
    article: Mapped["Article"] = relationship("Article", back_populates="event_articles")


class Brief(Base):
    __tablename__ = "briefs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    brief_type: Mapped[BriefType] = mapped_column(SAEnum(BriefType), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    raw_events: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    recipient_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    user_role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.other)
    language: Mapped[UserLanguage] = mapped_column(SAEnum(UserLanguage), default=UserLanguage.uz)
    topics: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    industries: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    regions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    companies_of_interest: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    send_time: Mapped[str] = mapped_column(String(10), default="08:00")
    format: Mapped[UserFormat] = mapped_column(SAEnum(UserFormat), default=UserFormat.standard)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    interest_weights: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_active_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SourceScoreHistory(Base):
    __tablename__ = "source_score_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("sources.id"), nullable=False)
    score_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    signal_score: Mapped[float] = mapped_column(Float, default=0.0)
    accuracy_score: Mapped[float] = mapped_column(Float, default=0.0)
    speed_score: Mapped[float] = mapped_column(Float, default=0.0)
    noise_penalty: Mapped[float] = mapped_column(Float, default=0.0)
    final_score: Mapped[float] = mapped_column(Float, default=0.0)
    tier: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    source: Mapped["Source"] = relationship("Source", back_populates="score_history")

    __table_args__ = (
        UniqueConstraint("source_id", "score_date", name="uq_source_score_date"),
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("events.id"), nullable=False)
    alert_type: Mapped[AlertType] = mapped_column(SAEnum(AlertType), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    recipient_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    event: Mapped["Event"] = relationship("Event", back_populates="alerts")
