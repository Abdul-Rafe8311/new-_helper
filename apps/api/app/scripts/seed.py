"""Seed the demo reader and the source registry. Idempotent: safe to run repeatedly.

Usage: python -m app.scripts.seed
"""

import asyncio
import secrets

import structlog
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.security import hash_password
from app.db.session import get_sessionmaker
from app.models import Depth, ReaderProfile, Source, User
from app.services.auth import get_user_by_email, normalise_email
from app.sources.registry import SourceSpec, load_registry

log = structlog.get_logger(__name__)

DEMO_TOPICS = {
    "world": 0.8,
    "pakistan": 0.9,
    "ai": 0.9,
    "tech": 0.7,
    "startups": 0.6,
    "markets": 0.5,
    "science": 0.6,
    "climate": 0.5,
    "cricket": 0.8,
    "design": 0.4,
}


async def seed_sources(session: AsyncSession, specs: list[SourceSpec]) -> int:
    for spec in specs:
        stmt = insert(Source).values(
            name=spec.name,
            kind=spec.kind,
            url=spec.url,
            topics=spec.topics,
            quality=spec.quality,
            high_value=spec.high_value,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[Source.url],
            set_={
                "name": spec.name,
                "kind": spec.kind,
                "topics": spec.topics,
                "high_value": spec.high_value,
            },
        )
        await session.execute(stmt)
    await session.commit()
    return len(specs)


async def seed_demo_user(session: AsyncSession, settings: Settings) -> bool:
    """Create the demo reader once; never overwrite a profile it has since learned."""
    if await get_user_by_email(session, settings.demo_email) is not None:
        return False
    session.add(
        User(
            email=normalise_email(settings.demo_email),
            # Nobody knows this password: the demo is entered only through POST /auth/demo.
            password_hash=hash_password(secrets.token_urlsafe(32)),
            display_name="Demo Reader",
            timezone="Asia/Karachi",
            city="Lahore",
            profile=ReaderProfile(
                onboarding_completed=True,
                topics=DEMO_TOPICS,
                keywords=["large language models", "PSL", "climate finance"],
                entities={
                    "people": [],
                    "companies": ["Anthropic", "Nvidia"],
                    "teams": ["Pakistan cricket team", "Lahore Qalandars"],
                    "places": ["Lahore", "Karachi"],
                },
                reading_minutes=15,
                depth=Depth.BALANCED,
                surprise_me=True,
                paper_name="The Morning Demo",
            ),
        )
    )
    await session.commit()
    return True


async def run_seed(settings: Settings) -> None:
    """Load the source registry and create the demo reader (used by the pipeline's seed stage)."""
    specs = load_registry()
    async with get_sessionmaker()() as session:
        sources = await seed_sources(session, specs)
        created = await seed_demo_user(session, settings)
    log.info("seed_done", sources=sources, demo_user_created=created)


async def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    await run_seed(settings)


if __name__ == "__main__":
    asyncio.run(main())
