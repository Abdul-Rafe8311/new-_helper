"""Plain data passed between retrieval, scoring, selection and the composer."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from app.models.enums import Depth


@dataclass(frozen=True, slots=True)
class ProfileView:
    """What ranking needs from a reader, detached from the ORM."""

    user_id: UUID
    first_name: str
    paper_name: str | None
    city: str | None
    timezone: str
    topics: dict[str, float]
    keywords: list[str]
    entities: dict[str, list[str]]
    blocked_topics: frozenset[str]
    blocked_keywords: tuple[str, ...]
    blocked_sources: tuple[str, ...]
    source_affinity: dict[str, float]
    reading_minutes: int
    depth: Depth
    surprise_me: bool
    interest_vector: list[float] | None
    context_notes: str | None
    # learned share of the paper for explore picks; None means the selection default
    explore_rate: float | None = None
    # entities the loop promoted (also listed in `entities`)
    learned_entities: dict[str, list[str]] = field(default_factory=dict)

    @property
    def terms(self) -> list[str]:
        """Keywords and entities, de-duplicated case-insensitively, order preserved."""
        seen: set[str] = set()
        out: list[str] = []
        for term in [*self.keywords, *(e for group in self.entities.values() for e in group)]:
            key = term.strip().lower()
            if key and key not in seen:
                seen.add(key)
                out.append(term.strip())
        return out

    def top_topics(self, n: int) -> list[str]:
        ranked = sorted(self.topics.items(), key=lambda kv: kv[1], reverse=True)
        return [slug for slug, w in ranked[:n] if w > 0]


@dataclass(frozen=True, slots=True)
class Candidate:
    """A summarised cluster representative that is eligible for today's paper."""

    id: UUID
    url: str
    title: str
    headline: str
    summary: str
    key_facts: tuple[str, ...]
    source_id: UUID | None
    source_name: str
    source_quality: float
    cluster_id: int | None
    cluster_size: int
    topics: dict[str, float]
    entities: dict[str, list[str]]
    embedding: list[float] | None
    published_at: datetime | None
    image_url: str | None
    # which retrieval arms found it: "vector", "keyword", "big_story"
    origins: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True, slots=True)
class Scored:
    candidate: Candidate
    score: float
    breakdown: dict[str, Any]
