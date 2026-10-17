"""reader_profiles.onboarding_state

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "reader_profiles",
        sa.Column(
            "onboarding_state",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    # the default only backfills existing rows; the ORM supplies the value afterwards
    op.alter_column("reader_profiles", "onboarding_state", server_default=None)


def downgrade() -> None:
    op.drop_column("reader_profiles", "onboarding_state")
