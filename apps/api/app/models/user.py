"""Readers and their personalisation profile."""

import uuid
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
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

    user: Mapped[User] = relationship(back_populates="profile", lazy="raise")
