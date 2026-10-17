"""Build the ORM-free ProfileView that ranking and the composer work from."""

from typing import Any

from app.models import ReaderProfile, User
from app.personalize.types import ProfileView


def first_name(display_name: str) -> str:
    return display_name.split()[0] if display_name.split() else display_name


def profile_view(user: User, profile: ReaderProfile) -> ProfileView:
    blocked: dict[str, Any] = profile.blocked or {}
    return ProfileView(
        user_id=user.id,
        first_name=first_name(user.display_name),
        paper_name=profile.paper_name,
        city=user.city,
        timezone=user.timezone,
        topics={k: float(v) for k, v in (profile.topics or {}).items()},
        keywords=list(profile.keywords or []),
        entities={k: list(v) for k, v in (profile.entities or {}).items()},
        blocked_topics=frozenset(blocked.get("topics", [])),
        blocked_keywords=tuple(blocked.get("keywords", [])),
        blocked_sources=tuple(blocked.get("sources", [])),
        source_affinity={k: float(v) for k, v in (profile.source_affinity or {}).items()},
        reading_minutes=profile.reading_minutes,
        depth=profile.depth,
        surprise_me=profile.surprise_me,
        interest_vector=list(profile.interest_vector)
        if profile.interest_vector is not None
        else None,
        context_notes=profile.context_notes,
    )
