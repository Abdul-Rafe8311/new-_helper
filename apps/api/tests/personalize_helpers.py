"""Builders for ranking tests (no database needed)."""

import itertools
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.models.enums import Depth
from app.personalize.types import Candidate, ProfileView

NOW = datetime(2026, 10, 17, 6, 0, tzinfo=UTC)
_seq = itertools.count(1)


def unit(*xs: float) -> list[float]:
    return list(xs)


def profile(**over: Any) -> ProfileView:
    base: dict[str, Any] = {
        "user_id": uuid4(),
        "first_name": "Sara",
        "paper_name": "The Sara Morning",
        "city": "Lahore",
        "timezone": "Asia/Karachi",
        "topics": {},
        "keywords": [],
        "entities": {"people": [], "companies": [], "teams": [], "places": []},
        "blocked_topics": frozenset(),
        "blocked_keywords": (),
        "blocked_sources": (),
        "source_affinity": {},
        "reading_minutes": 10,
        "depth": Depth.BALANCED,
        "surprise_me": True,
        "interest_vector": None,
        "context_notes": None,
    }
    base.update(over)
    return ProfileView(**base)


def candidate(**over: Any) -> Candidate:
    n = next(_seq)
    base: dict[str, Any] = {
        "id": uuid4(),
        "url": f"https://example.com/{n}",
        "title": f"Title {n}",
        "headline": f"Headline {n}",
        "summary": f"Summary {n}.",
        "key_facts": ("a", "b", "c"),
        "source_id": uuid4(),
        "source_name": f"Source {n}",
        "source_quality": 0.8,
        "cluster_id": n,
        "cluster_size": 1,
        "topics": {},
        "entities": {},
        "embedding": None,
        "published_at": NOW,
        "image_url": None,
        "origins": frozenset(),
    }
    base.update(over)
    return Candidate(**base)


def uid(n: int) -> UUID:
    return UUID(int=n)


def selection(score: float = 0.5, *, explore: bool = False, why: str = "why", **over: Any) -> Any:
    """A Selection around a fresh candidate."""
    from app.personalize.select import Selection
    from app.personalize.types import Scored

    c = candidate(**over)
    return Selection(Scored(c, score, {"components": {}, "raw": {}}), explore, why)
