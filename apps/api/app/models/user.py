"""Readers and their personalisation profile."""

import uuid
from typing import Any

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps, UUIDPrimaryKey
from app.models.enums import Depth, pg_enum

EMBEDDING_DIM = 384


def default_entities() -> dict[str, list[str]]:
    return {"people": [], "companies": [], "teams": [], "places": []}


def default_blocked() -> dict[str, list[str]]:
    return {"topics": [], "keywords": [], "sources": []}


class User(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Karachi")
    city: Mapped[str | None] = mapped_column(String(120))

    profile: Mapped["ReaderProfile"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan", lazy="raise"
    )


class ReaderProfile(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "reader_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # {slug: weight 0..1}
    topics: Mapped[dict[str, float]] = mapped_column(JSONB, nullable=False, default=dict)
    keywords: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    # {"people": [...], "companies": [...], "teams": [...], "places": [...]}
    entities: Mapped[dict[str, list[str]]] = mapped_column(
        JSONB, nullable=False, default=default_entities
    )
    # {"topics": [...], "keywords": [...], "sources": [...]}
    blocked: Mapped[dict[str, list[str]]] = mapped_column(
        JSONB, nullable=False, default=default_blocked
    )
    # {source_id: affinity}
    source_affinity: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    reading_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    depth: Mapped[Depth] = mapped_column(
        pg_enum(Depth, "depth"), nullable=False, default=Depth.BALANCED
    )
    surprise_me: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    interest_vector: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    paper_name: Mapped[str | None] = mapped_column(String(120))
    context_notes: Mapped[str | None] = mapped_column(Text)
    # Autosaved onboarding answers, so a refresh loses nothing; see app.onboarding.state
    onboarding_state: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    # Learned by the T11 loop. Promoted entities are also listed in `entities`; this marks them.
    learned_entities: Mapped[dict[str, list[str]]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=sa.text("'{}'::jsonb")
    )
    # Share of the paper given to explore picks; null means the default (SelectionConfig).
    explore_rate: Mapped[float | None] = mapped_column(Float)
    # Learner bookkeeping: watermark, entity and less-like tallies, per-source stats, settled items
    learn_state: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=sa.text("'{}'::jsonb")
    )

    user: Mapped[User] = relationship(back_populates="profile", lazy="raise")


class ProfileChange(UUIDPrimaryKey, Timestamps, Base):
    """One change the learner made to a profile: what, by how much, and which signals caused it."""

    __tablename__ = "profile_changes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # topic_weight | interest_vector | entity_promoted | topic_blocked | source_affinity |
    # explore_rate | explore_graduated
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    key: Mapped[str | None] = mapped_column(String(200))
    before: Mapped[Any] = mapped_column(JSONB)
    after: Mapped[Any] = mapped_column(JSONB)
    # signed size of the change; for the interest vector, 1 - cosine(old, new)
    delta: Mapped[float | None] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    # the strongest events behind it: [{"type", "article_id", "weight"}]
    signals: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    run: Mapped[str] = mapped_column(String(16), nullable=False, default="nightly")
