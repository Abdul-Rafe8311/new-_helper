"""Daily editions, their items, reader events and pipeline runs."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps, UUIDPrimaryKey
from app.models.enums import EditionStatus, EventType, RunStatus, Slot, pg_enum


class Edition(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "editions"
    __table_args__ = (UniqueConstraint("user_id", "edition_date"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    edition_date: Mapped[date] = mapped_column(Date, nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[EditionStatus] = mapped_column(
        pg_enum(EditionStatus, "edition_status"), nullable=False, default=EditionStatus.PENDING
    )
    title: Mapped[str | None] = mapped_column(Text)
    editor_note: Mapped[str | None] = mapped_column(Text)
    layout: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    pdf_path: Mapped[str | None] = mapped_column(Text)
    pdf_hash: Mapped[str | None] = mapped_column(String(64))
    audio_path: Mapped[str | None] = mapped_column(Text)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stats: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    items: Mapped[list["EditionItem"]] = relationship(
        back_populates="edition",
        cascade="all, delete-orphan",
        order_by="EditionItem.position",
        lazy="raise",
    )


class EditionItem(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "edition_items"

    edition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("editions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section: Mapped[str] = mapped_column(String(120), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    slot: Mapped[Slot] = mapped_column(pg_enum(Slot, "slot"), nullable=False)
    headline: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    why_text: Mapped[str | None] = mapped_column(Text)
    score: Mapped[float | None] = mapped_column(Float)
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    edition: Mapped[Edition] = relationship(back_populates="items", lazy="raise")


class ReaderEvent(Base):
    __tablename__ = "reader_events"
    __table_args__ = (Index("ix_reader_events_user_id_created_at", "user_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    edition_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("editions.id", ondelete="SET NULL")
    )
    article_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("articles.id", ondelete="SET NULL")
    )
    edition_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("edition_items.id", ondelete="SET NULL")
    )
    type: Mapped[EventType] = mapped_column(pg_enum(EventType, "event_type"), nullable=False)
    value: Mapped[float | None] = mapped_column(Float)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PipelineRun(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "pipeline_runs"

    stage: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[RunStatus] = mapped_column(
        pg_enum(RunStatus, "run_status"), nullable=False, default=RunStatus.RUNNING
    )
    stats: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
