"""Shared AI bookkeeping: LLM spend and the taxonomy's topic vectors."""

from pgvector.sqlalchemy import Vector
from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UUIDPrimaryKey
from app.models.user import EMBEDDING_DIM


class LLMUsage(UUIDPrimaryKey, Timestamps, Base):
    """One row per LLM call; the daily budget guard sums cost_usd."""

    __tablename__ = "llm_usage"

    model: Mapped[str] = mapped_column(String(100), nullable=False)
    purpose: Mapped[str] = mapped_column(String(64), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_write_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class TopicPrototype(Base):
    """Embedding of a taxonomy topic description. The API reads it, never the model."""

    __tablename__ = "topic_prototypes"

    slug: Mapped[str] = mapped_column(String(64), primary_key=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
