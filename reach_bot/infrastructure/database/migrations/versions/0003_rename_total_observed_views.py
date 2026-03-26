"""Rename total_confirmed_reach to total_observed_views

Причина переименования:
  total_confirmed_reach — технически некорректное название.
  Метрика представляет собой сумму наблюдаемых просмотров (manba + ikkilamchi),
  а не уникальный охват аудитории. Новое название total_observed_views
  честно отражает смысл метрики.

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-26
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "analysis_runs",
        "total_confirmed_reach",
        new_column_name="total_observed_views",
    )


def downgrade() -> None:
    op.alter_column(
        "analysis_runs",
        "total_observed_views",
        new_column_name="total_confirmed_reach",
    )
