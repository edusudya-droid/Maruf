"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-24 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column(
            "role",
            sa.String(50),
            nullable=False,
            comment="SUPERADMIN|ADMIN|ANALYST|VIEWER",
        ),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("telegram_user_id", name="uq_users_telegram_user_id"),
        sa.CheckConstraint(
            "role IN ('SUPERADMIN','ADMIN','ANALYST','VIEWER')", name="ck_users_role"
        ),
        sa.CheckConstraint("status IN ('ACTIVE','BLOCKED')", name="ck_users_status"),
    )

    op.create_table(
        "official_channel",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("telegram_channel_id", sa.BigInteger(), nullable=False),
        sa.Column("channel_title", sa.String(255), nullable=False),
        sa.Column("channel_url", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "source_posts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "official_channel_id",
            sa.BigInteger(),
            sa.ForeignKey("official_channel.id"),
            nullable=False,
        ),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=False),
        sa.Column("post_url", sa.Text(), nullable=False),
        sa.Column("post_text", sa.Text(), nullable=True),
        sa.Column("published_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("views_count", sa.BigInteger(), nullable=True),
        sa.Column("collected_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint(
            "official_channel_id", "telegram_message_id", name="uq_channel_message"
        ),
    )

    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "source_post_id",
            sa.BigInteger(),
            sa.ForeignKey("source_posts.id"),
            nullable=False,
        ),
        sa.Column(
            "started_by_user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(50), nullable=False, server_default="PENDING"),
        sa.Column("started_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("finished_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("source_views", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("confirmed_secondary_views", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_confirmed_reach", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("counted_posts_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_posts_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('PENDING','RUNNING','COMPLETED','COMPLETED_WITH_SKIPS','FAILED')",
            name="ck_analysis_runs_status",
        ),
    )

    op.create_table(
        "detected_posts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "analysis_run_id",
            sa.BigInteger(),
            sa.ForeignKey("analysis_runs.id"),
            nullable=False,
        ),
        sa.Column(
            "source_post_id",
            sa.BigInteger(),
            sa.ForeignKey("source_posts.id"),
            nullable=False,
        ),
        sa.Column("external_channel_name", sa.String(255), nullable=True),
        sa.Column("external_channel_id", sa.BigInteger(), nullable=True),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=True),
        sa.Column("post_url", sa.Text(), nullable=True),
        sa.Column("post_text", sa.Text(), nullable=True),
        sa.Column("published_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("views_count", sa.BigInteger(), nullable=True),
        sa.Column("confirmation_type", sa.String(60), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("skip_reason", sa.String(100), nullable=True),
        sa.Column("text_similarity_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint(
            "confirmation_type IN ("
            "'FORWARD_CONFIRMED','SOURCE_LINK_CONFIRMED',"
            "'FULL_TEXT_COPY_CONFIRMED','NEAR_FULL_TEXT_COPY_CONFIRMED')",
            name="ck_detected_posts_confirmation_type",
        ),
        sa.CheckConstraint(
            "status IN ("
            "'COUNTED','SKIPPED_UNAVAILABLE','SKIPPED_DUPLICATE',"
            "'SKIPPED_NO_VIEWS','SKIPPED_LOW_SIMILARITY','SKIPPED_UNCONFIRMED','ERROR')",
            name="ck_detected_posts_status",
        ),
    )

    op.create_table(
        "system_settings",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("setting_key", sa.String(100), nullable=False),
        sa.Column("setting_value", sa.Text(), nullable=False),
        sa.Column(
            "updated_by_user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("setting_key", name="uq_system_settings_key"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action_type", sa.String(100), nullable=False),
        sa.Column("object_type", sa.String(100), nullable=True),
        sa.Column("object_id", sa.String(100), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "error_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "analysis_run_id", sa.BigInteger(), sa.ForeignKey("analysis_runs.id"), nullable=True
        ),
        sa.Column(
            "detected_post_id", sa.BigInteger(), sa.ForeignKey("detected_posts.id"), nullable=True
        ),
        sa.Column("error_code", sa.String(100), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("NOW()")),
    )

    # Seed default system settings
    op.execute(
        """
        INSERT INTO system_settings (setting_key, setting_value, updated_at) VALUES
            ('near_full_similarity_threshold', '0.90', NOW()),
            ('unavailable_retry_limit', '2', NOW()),
            ('history_retention_days', 'null', NOW()),
            ('max_daily_analyses', '20', NOW()),
            ('max_visible_posts', '20', NOW())
        """
    )


def downgrade() -> None:
    op.drop_table("error_logs")
    op.drop_table("audit_logs")
    op.drop_table("system_settings")
    op.drop_table("detected_posts")
    op.drop_table("analysis_runs")
    op.drop_table("source_posts")
    op.drop_table("official_channel")
    op.drop_table("users")
