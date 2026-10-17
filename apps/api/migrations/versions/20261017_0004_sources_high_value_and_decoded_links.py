"""sources high_value and decoded_links

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-17 15:04:29.116431
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "decoded_links",
        sa.Column("google_url", sa.Text(), nullable=False),
        sa.Column("publisher_url", sa.Text(), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_decoded_links")),
        sa.UniqueConstraint("google_url", name=op.f("uq_decoded_links_google_url")),
    )
    op.add_column(
        "sources", sa.Column("high_value", sa.Boolean(), server_default=sa.false(), nullable=False)
    )


def downgrade() -> None:
    op.drop_column("sources", "high_value")
    op.drop_table("decoded_links")
