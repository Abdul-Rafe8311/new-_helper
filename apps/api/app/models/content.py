"""Sources and the articles fetched from them (shared by all readers)."""

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UUIDPrimaryKey
from app.models.enums import SourceKind, pg_enum
from app.models.user import EMBEDDING_DIM


class Source(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "sources"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[SourceKind] = mapped_column(pg_enum(SourceKind, "source_kind"), nullable=False)
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    topics: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    quality: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Worth a paid extraction fallback (Apify) when open-source extraction fails.
    high_value: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=sa.false()
    )
    etag: Mapped[str | None] = mapped_column(String(255))
    last_modified: Mapped[str | None] = mapped_column(String(255))
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Article(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "articles"
    __table_args__ = (
        Index(
            "ix_articles_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sources.id", ondelete="SET NULL"), index=True
    )
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)  # canonical
    title: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str | None] = mapped_column(String(300))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    language: Mapped[str | None] = mapped_column(String(16))
    image_url: Mapped[str | None] = mapped_column(Text)
    excerpt: Mapped[str | None] = mapped_column(Text)
    content_text: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    word_count: Mapped[int | None] = mapped_column(Integer)
    topics: Mapped[dict[str, float]] = mapped_column(JSONB, nullable=False, default=dict)
    entities: Mapped[dict[str, list[str]]] = mapped_column(JSONB, nullable=False, default=dict)
    headline: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    key_facts: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    summary_model: Mapped[str | None] = mapped_column(String(100))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    cluster_id: Mapped[int | None] = mapped_column(Integer, index=True)
    cluster_size: Mapped[int | None] = mapped_column(Integer)


class DecodedLink(UUIDPrimaryKey, Timestamps, Base):
    """Cache of Google News redirect links resolved to publisher URLs (decoding is rate-limited)."""

    __tablename__ = "decoded_links"

    google_url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    publisher_url: Mapped[str] = mapped_column(Text, nullable=False)
