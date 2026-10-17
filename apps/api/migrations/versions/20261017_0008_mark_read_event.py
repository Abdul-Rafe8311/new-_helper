"""event_type: mark_read

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-17
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # "read" (expanded in place, or Shift+A) is weaker evidence of interest than "open", so it
    # gets its own event instead of being logged as one.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE event_type ADD VALUE IF NOT EXISTS 'mark_read'")


def downgrade() -> None:
    # Postgres cannot drop one value from an enum; an unused extra value is harmless.
    pass
