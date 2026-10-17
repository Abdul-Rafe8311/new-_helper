"""weather_cache

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-17 17:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "weather_cache",
        sa.Column("city_key", sa.String(length=120), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_weather_cache")),
        sa.UniqueConstraint("city_key", "day", name=op.f("uq_weather_cache_city_key")),
    )


def downgrade() -> None:
    op.drop_table("weather_cache")
