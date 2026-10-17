"""Edition service: generate one reader's paper for one date.

generate_edition() is idempotent: there is one edition per (user, date); asking again returns the
existing one unless `force` is set (limited to 3 regenerations a day). The work is split so the
API can answer immediately and finish in the background:

    prepare()  create/reserve the edition row as `pending`        (fast, in the request)
    build()    retrieve -> score -> select -> compose -> persist  (slow, in the background)
"""

import uuid
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.ai.llm import LLMProvider
from app.ai.usage import BudgetGuard, track_usage
from app.core.errors import AppError
from app.editions.compose import ComposeInput, Composition, compose_edition
from app.editions.weather import Weather, WeatherService
from app.models import Edition, EditionItem, EditionStatus, Slot, User
from app.models.enums import Depth
from app.personalize.config import (
    DEFAULT_SCORING,
    DEFAULT_SELECTION,
    ScoringConfig,
    SelectionConfig,
)
from app.personalize.profile import profile_view
from app.personalize.retrieve import previously_seen, retrieve_candidates
from app.personalize.score import score_all
from app.personalize.select import Selection, select_items, topic_label

log = structlog.get_logger(__name__)

# progress shown to the reader while a paper is being built (onboarding's printing-press finale)
STAGES = ("gathering", "choosing", "writing", "typesetting")
MAX_REGENERATIONS_PER_DAY = 3
STALE_PENDING = timedelta(minutes=15)  # a pending edition this old lost its worker
LAYOUT_VERSION = 1


class NoArticlesError(Exception):
    """Nothing eligible to print today (empty pool after exclusions)."""


def local_date(timezone: str, now: datetime) -> date:
    try:
        return now.astimezone(ZoneInfo(timezone)).date()
    except ZoneInfoNotFoundError:
        return now.astimezone(UTC).date()


@dataclass(frozen=True, slots=True)
class Prepared:
    edition: Edition
    needs_build: bool


def assign_slot(
    selection: Selection, *, is_lead: bool, first_in_section: bool, depth: Depth
) -> Slot:
    if is_lead:
        return Slot.LEAD
    if selection.explore:
        return Slot.EXPLORE
    if depth is Depth.BRIEF:
        return Slot.BRIEF
    return Slot.FEATURE if first_in_section else Slot.STANDARD


class EditionService:
    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        llm: LLMProvider | None,
        smart_model: str,
        *,
        weather: WeatherService | None = None,
        guard: BudgetGuard | None = None,
        scoring: ScoringConfig = DEFAULT_SCORING,
        selection: SelectionConfig = DEFAULT_SELECTION,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._sessionmaker = sessionmaker
        self._llm = llm
        self._model = smart_model
        self._weather = weather
        self._guard = guard
        self._scoring = scoring
        self._selection = selection
        self._clock = clock

    # --- reserving -----------------------------------------------------------------------

    async def prepare(
        self, session: AsyncSession, user_id: uuid.UUID, edition_date: date, *, force: bool = False
    ) -> Prepared:
        """Return the edition for this reader and date, and whether it still needs building."""
        edition = await self._existing(session, user_id, edition_date)
        if edition is None:
            return await self._create(session, user_id, edition_date)
        if edition.status is EditionStatus.PENDING:
            stale = self._clock() - edition.updated_at > STALE_PENDING
            if stale:
                await self._reset(session, edition)
            return Prepared(edition, needs_build=stale)
        if edition.status is EditionStatus.FAILED:
            await self._reset(session, edition)
            return Prepared(edition, needs_build=True)
        if not force:
            return Prepared(edition, needs_build=False)
        used = int(edition.stats.get("regenerations", 0))
        if used >= MAX_REGENERATIONS_PER_DAY:
            raise AppError(
                429,
                "regeneration_limit",
                f"You can regenerate a paper {MAX_REGENERATIONS_PER_DAY} times a day",
            )
        await self._reset(session, edition, regenerations=used + 1)
        return Prepared(edition, needs_build=True)

    @staticmethod
    async def _existing(session: AsyncSession, user_id: uuid.UUID, day: date) -> Edition | None:
        return await session.scalar(
            select(Edition).where(Edition.user_id == user_id, Edition.edition_date == day)
        )

    async def _create(self, session: AsyncSession, user_id: uuid.UUID, day: date) -> Prepared:
        number = (
            await session.scalar(select(func.max(Edition.number)).where(Edition.user_id == user_id))
            or 0
        ) + 1
        edition = Edition(
            user_id=user_id,
            edition_date=day,
            number=number,
            status=EditionStatus.PENDING,
            stats={"regenerations": 0},
        )
        try:
            async with session.begin_nested():
                session.add(edition)
        except IntegrityError:  # another worker reserved it first
            if edition in session:
                session.expunge(edition)
            existing = await self._existing(session, user_id, day)
            if existing is None:
                raise
            return Prepared(existing, needs_build=False)
        await session.commit()
        return Prepared(edition, needs_build=True)

    @staticmethod
    async def _reset(
        session: AsyncSession, edition: Edition, *, regenerations: int | None = None
    ) -> None:
        stats = {"regenerations": int(edition.stats.get("regenerations", 0))}
        if regenerations is not None:
            stats["regenerations"] = regenerations
        edition.status = EditionStatus.PENDING
        edition.stats = stats
        await session.commit()

    # --- building ------------------------------------------------------------------------

    async def generate_edition(
        self, session: AsyncSession, user_id: uuid.UUID, edition_date: date, *, force: bool = False
    ) -> Edition:
        prepared = await self.prepare(session, user_id, edition_date, force=force)
        if prepared.needs_build:
            await self.build(session, prepared.edition.id)
            await session.refresh(prepared.edition)
        return prepared.edition

    async def run(self, edition_id: uuid.UUID) -> None:
        """Background entry point: builds in its own session."""
        async with self._sessionmaker() as session:
            await self.build(session, edition_id)

    async def build(self, session: AsyncSession, edition_id: uuid.UUID) -> None:
        """Fill a pending edition. Never raises for content problems: the edition is marked
        failed (with the reason in stats) so one reader's trouble cannot stop the others."""
        edition = await session.get(Edition, edition_id)
        if edition is None:
            raise LookupError(f"edition {edition_id} does not exist")
        regenerations = int(edition.stats.get("regenerations", 0))
        started = self._clock()
        try:
            with track_usage() as calls:
                stats = await self._fill(session, edition)
            stats["llm_calls"] = len(calls)
            stats["llm_cost_usd"] = round(sum(c.cost_usd for c in calls), 6)
            stats["regenerations"] = regenerations
            stats["stage"] = "done"
            stats["seconds"] = round((self._clock() - started).total_seconds(), 2)
            edition.stats = stats
            edition.status = EditionStatus.READY
            edition.generated_at = self._clock()
            await session.commit()
        except Exception as exc:
            await session.rollback()
            log.exception("edition_failed", edition_id=str(edition_id))
            edition = await session.get(Edition, edition_id)
            if edition is not None:
                edition.status = EditionStatus.FAILED
                edition.stats = {
                    "regenerations": regenerations,
                    "error": f"{type(exc).__name__}: {exc}"[:300],
                }
                await session.commit()

    @staticmethod
    async def _stage(session: AsyncSession, edition: Edition, stage: str) -> None:
        edition.stats = {**edition.stats, "stage": stage}
        await session.commit()

    async def _fill(self, session: AsyncSession, edition: Edition) -> dict[str, Any]:
        user = await session.scalar(
            select(User).options(selectinload(User.profile)).where(User.id == edition.user_id)
        )
        if user is None:
            raise LookupError("reader no longer exists")
        profile = profile_view(user, user.profile)
        now = self._clock()

        await self._stage(session, edition, STAGES[0])
        candidates = await retrieve_candidates(session, profile, edition.edition_date, now=now)
        seen = await previously_seen(session, user.id)
        await self._stage(session, edition, STAGES[1])
        scored = score_all(candidates, profile, now, self._scoring, seen)
        selections = select_items(scored, profile, self._selection)
        if not selections:
            raise NoArticlesError(f"no eligible articles among {len(candidates)} candidates")

        await self._stage(session, edition, STAGES[2])
        weather = (
            await self._weather.for_city(session, user.city, edition.edition_date)
            if self._weather
            else None
        )
        composition = await compose_edition(
            ComposeInput(profile, selections, edition.edition_date, weather),
            self._llm,
            self._model,
            self._guard,
        )
        await self._stage(session, edition, STAGES[3])
        await self._persist(
            session,
            edition,
            profile.paper_name,
            user.city,
            profile.depth,
            selections,
            composition,
            weather,
        )
        return self._stats(len(candidates), selections, composition)

    async def _persist(
        self,
        session: AsyncSession,
        edition: Edition,
        paper_name: str | None,
        city: str | None,
        depth: Depth,
        selections: list[Selection],
        composition: Composition,
        weather: Weather | None,
    ) -> None:
        by_article = {s.scored.candidate.id: s for s in selections}
        # two builds of one edition (e.g. a stale-pending retry) take turns instead of interleaving
        await session.refresh(edition, with_for_update=True)
        await session.execute(delete(EditionItem).where(EditionItem.edition_id == edition.id))
        item_ids: dict[uuid.UUID, uuid.UUID] = {}
        layout_sections: list[dict[str, Any]] = []
        position = 0
        for section in composition.sections:
            members: list[str] = []
            for index, article_id in enumerate(section.article_ids):
                selection = by_article[article_id]
                headline, summary = composition.copy[article_id]
                item_id = item_ids[article_id] = uuid.uuid4()
                session.add(
                    EditionItem(
                        id=item_id,
                        edition_id=edition.id,
                        article_id=article_id,
                        section=section.name,
                        position=position,
                        slot=assign_slot(
                            selection,
                            is_lead=article_id == composition.lead,
                            first_in_section=index == 0,
                            depth=depth,
                        ),
                        headline=headline,
                        summary=summary,
                        why_text=selection.why,
                        score=selection.scored.score,
                        score_breakdown=selection.scored.breakdown,
                    )
                )
                members.append(str(item_id))
                position += 1
            layout_sections.append({"name": section.name, "item_ids": members})
        quote = dict(composition.quote) if composition.quote else None
        if quote:
            quote["item_id"] = str(item_ids[uuid.UUID(quote["article_id"])])
        edition.title = composition.title_line
        edition.editor_note = composition.editor_note
        edition.layout = {
            "version": LAYOUT_VERSION,
            "tagline": composition.tagline,
            "lead_item_id": str(item_ids[composition.lead]),
            "sections": layout_sections,
            "three_things": composition.three_things,
            "quote": quote,
            "quiz": composition.quiz,
            "masthead": {
                "paper_name": paper_name,
                "city": city,
                "weather": weather.model_dump() if weather else None,
            },
            "composed_by": composition.source,
            "fallback_reason": composition.fallback_reason,
        }

    @staticmethod
    def _stats(pool: int, selections: list[Selection], composition: Composition) -> dict[str, Any]:
        cands = [s.scored.candidate for s in selections]
        strongest = Counter(max(c.topics, key=lambda t: c.topics[t]) for c in cands if c.topics)
        return {
            "candidates": pool,
            "items": len(selections),
            "sources": len({c.source_id for c in cands}),
            "topics": len(strongest),
            "top_topics": [topic_label(t) for t, _ in strongest.most_common(3)],
            "explore_items": sum(s.explore for s in selections),
            "sections": len(composition.sections),
            "composed_by": composition.source,
            "fallback_reason": composition.fallback_reason,
        }
