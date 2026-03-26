"""Add discovery_method, channel_username, raw_metadata to detected_posts

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-25 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "detected_posts",
        sa.Column("discovery_method", sa.String(50), nullable=True),
    )
    op.add_column(
        "detected_posts",
        sa.Column("channel_username", sa.String(255), nullable=True),
    )
    op.add_column(
        "detected_posts",
        sa.Column("raw_metadata", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("detected_posts", "raw_metadata")
    op.drop_column("detected_posts", "channel_username")
    op.drop_column("detected_posts", "discovery_method")
