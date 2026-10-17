"""editions.pdf_hash

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # fingerprint of the content the stored PDF was rendered from; a match means no re-render
    op.add_column("editions", sa.Column("pdf_hash", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("editions", "pdf_hash")
