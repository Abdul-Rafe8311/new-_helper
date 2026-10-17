"""First-edition generation behind an interface.

Onboarding only depends on `EditionGenerator` and on the `stage` the generator writes to
`Edition.stats` (see `app.editions.service.STAGES`, then "done").
"""

from typing import Protocol
from uuid import UUID

from app.editions.service import STAGES, EditionService

__all__ = ["STAGES", "ComposerEditionGenerator", "EditionGenerator"]


class EditionGenerator(Protocol):
    async def generate(self, edition_id: UUID) -> None:
        """Build the edition, moving stats["stage"] through STAGES, then mark it ready or failed."""


class ComposerEditionGenerator:
    """Builds the pending edition with the real ranker and composer."""

    def __init__(self, service: EditionService) -> None:
        self._service = service

    async def generate(self, edition_id: UUID) -> None:
        await self._service.run(edition_id)
