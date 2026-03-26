from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.connection import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    username: Mapped[Optional[str]] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(back_populates="started_by_user")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")


class OfficialChannel(Base):
    __tablename__ = "official_channel"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    channel_title: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_url: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    source_posts: Mapped[list["SourcePost"]] = relationship(back_populates="official_channel")


class SourcePost(Base):
    __tablename__ = "source_posts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    official_channel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("official_channel.id"), nullable=False
    )
    telegram_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    post_url: Mapped[str] = mapped_column(Text, nullable=False)
    post_text: Mapped[Optional[str]] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(nullable=False)
    views_count: Mapped[Optional[int]] = mapped_column(BigInteger)
    collected_at: Mapped[datetime] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("official_channel_id", "telegram_message_id", name="uq_channel_message"),
    )

    official_channel: Mapped["OfficialChannel"] = relationship(back_populates="source_posts")
    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(back_populates="source_post")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_post_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("source_posts.id"), nullable=False
    )
    started_by_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING")
    started_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    source_views: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    confirmed_secondary_views: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    # Переименовано: total_confirmed_reach -> total_observed_views
    # Причина: это не уникальный охват, а сумма наблюдаемых просмотров.
    total_observed_views: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    counted_posts_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_posts_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    source_post: Mapped["SourcePost"] = relationship(back_populates="analysis_runs")
    started_by_user: Mapped["User"] = relationship(back_populates="analysis_runs")
    detected_posts: Mapped[list["DetectedPost"]] = relationship(back_populates="analysis_run")
    error_logs: Mapped[list["ErrorLog"]] = relationship(back_populates="analysis_run")


class DetectedPost(Base):
    __tablename__ = "detected_posts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    analysis_run_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("analysis_runs.id"), nullable=False
    )
    source_post_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("source_posts.id"), nullable=False
    )
    external_channel_name: Mapped[Optional[str]] = mapped_column(String(255))
    external_channel_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    telegram_message_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    post_url: Mapped[Optional[str]] = mapped_column(Text)
    post_text: Mapped[Optional[str]] = mapped_column(Text)
    published_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    views_count: Mapped[Optional[int]] = mapped_column(BigInteger)
    confirmation_type: Mapped[Optional[str]] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    skip_reason: Mapped[Optional[str]] = mapped_column(String(100))
    text_similarity_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    discovery_method: Mapped[Optional[str]] = mapped_column(String(50))
    channel_username: Mapped[Optional[str]] = mapped_column(String(255))
    raw_metadata: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    analysis_run: Mapped["AnalysisRun"] = relationship(back_populates="detected_posts")
    error_logs: Mapped[list["ErrorLog"]] = relationship(back_populates="detected_post")


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    setting_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    setting_value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_by_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"))
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    object_type: Mapped[Optional[str]] = mapped_column(String(100))
    object_id: Mapped[Optional[str]] = mapped_column(String(100))
    details: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    user: Mapped[Optional["User"]] = relationship(back_populates="audit_logs")


class ErrorLog(Base):
    __tablename__ = "error_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    analysis_run_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("analysis_runs.id")
    )
    detected_post_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("detected_posts.id")
    )
    error_code: Mapped[str] = mapped_column(String(100), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    analysis_run: Mapped[Optional["AnalysisRun"]] = relationship(back_populates="error_logs")
    detected_post: Mapped[Optional["DetectedPost"]] = relationship(back_populates="error_logs")
