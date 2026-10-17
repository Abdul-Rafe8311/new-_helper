"""First-edition generation behind an interface.

Task 8 replaces `StubEditionGenerator` with the real ranker and composer; onboarding only
depends on `EditionGenerator` and on the `stage` the generator writes to `Edition.stats`.
"""

import asyncio
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Edition, EditionStatus

log = structlog.get_logger(__name__)

STAGES = ("gathering", "choosing", "writing", "typesetting")

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


class EditionGenerator(Protocol):
    async def generate(self, edition_id: UUID) -> None:
        """Build the edition, moving stats["stage"] through STAGES, then mark it ready or failed."""


async def set_stage(session: AsyncSession, edition: Edition, stage: str) -> None:
    edition.stats = {**edition.stats, "stage": stage}
    await session.commit()


class StubEditionGenerator:
    """Marks the edition ready with placeholder content, walking through the stages."""

    def __init__(self, session_factory: SessionFactory, stage_seconds: float = 1.2) -> None:
        self._session_factory = session_factory
        self._stage_seconds = stage_seconds

    async def generate(self, edition_id: UUID) -> None:
        try:
            async with self._session_factory() as session:
                edition = await session.get(Edition, edition_id)
                if edition is None:
                    return
                for stage in STAGES:
                    await set_stage(session, edition, stage)
                    await asyncio.sleep(self._stage_seconds)
                edition.status = EditionStatus.READY
                edition.generated_at = datetime.now(UTC)
                edition.editor_note = "Your first edition is on its way. This is a placeholder."
                edition.layout = {"placeholder": True}
                edition.stats = {**edition.stats, "stage": "done"}
                await session.commit()
        except Exception:
            log.exception("edition_generation_failed", edition_id=str(edition_id))
            await self._mark_failed(edition_id)

    async def _mark_failed(self, edition_id: UUID) -> None:
        async with self._session_factory() as session:
            edition = await session.get(Edition, edition_id)
            if edition is not None:
                edition.status = EditionStatus.FAILED
                await session.commit()
