"""add release_date column to games

Revision ID: 0002_add_release_date
Revises: 0001_initial
Create Date: 2026-06-14 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_release_date"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "games",
        sa.Column("release_date", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("games", "release_date")
