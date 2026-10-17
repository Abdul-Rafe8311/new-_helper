"""The `compose` pipeline stage: one paper per onboarded reader, dated in their own timezone."""

import asyncio
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from uuid import UUID

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.factory import build_llm
from app.ai.usage import BudgetGuard
from app.core.config import Settings
from app.db.session import get_sessionmaker
from app.editions.service import EditionService, local_date
from app.editions.weather import WeatherService
from app.models import EditionStatus, PipelineRun, ReaderProfile, RunStatus, User

log = structlog.get_logger(__name__)

CONCURRENCY = 5


@dataclass
class ComposeReport:
    readers: int = 0
    built: int = 0
    already_done: int = 0
    failed: int = 0
    fallback_layouts: int = 0
    items: int = 0
    llm_calls: int = 0
    llm_cost_usd: float = 0.0


@dataclass(frozen=True, slots=True)
class Reader:
    id: UUID
    timezone: str


async def list_readers(session: AsyncSession, email: str | None = None) -> list[Reader]:
    stmt = (
        select(User.id, User.timezone)
        .join(ReaderProfile, ReaderProfile.user_id == User.id)
        .where(ReaderProfile.onboarding_completed.is_(True))
        .order_by(User.email)
    )
    if email:
        stmt = stmt.where(User.email == email.strip().lower())
    return [Reader(i, tz) for i, tz in (await session.execute(stmt)).all()]


async def run_bounded[T](
    items: Iterable[T], work: Callable[[T], Awaitable[None]], limit: int = CONCURRENCY
) -> None:
    """Run `work` on every item, at most `limit` at once; one failure never stops the rest."""
    gate = asyncio.Semaphore(limit)

    async def one(item: T) -> None:
        async with gate:
            try:
                await work(item)
            except Exception:
                log.exception("compose_reader_crashed")

    await asyncio.gather(*(one(i) for i in items))


async def run_compose(
    sessionmaker: async_sessionmaker[AsyncSession],
    service: EditionService,
    *,
    now: datetime | None = None,
    user_email: str | None = None,
    concurrency: int = CONCURRENCY,
) -> ComposeReport:
    now = now or datetime.now(UTC)
    async with sessionmaker() as session:
        readers = await list_readers(session, user_email)
    report = ComposeReport(readers=len(readers))

    async def compose_one(reader: Reader) -> None:
        day: date = local_date(reader.timezone, now)
        try:
            async with sessionmaker() as session:
                prepared = await service.prepare(session, reader.id, day)
                if not prepared.needs_build:
                    report.already_done += 1
                    return
                await service.build(session, prepared.edition.id)
                await session.refresh(prepared.edition)
                edition = prepared.edition
        except Exception:
            report.failed += 1
            raise
        if edition.status is not EditionStatus.READY:
            report.failed += 1
            return
        report.built += 1
        report.items += int(edition.stats.get("items", 0))
        report.llm_calls += int(edition.stats.get("llm_calls", 0))
        report.llm_cost_usd += float(edition.stats.get("llm_cost_usd", 0.0))
        report.fallback_layouts += edition.stats.get("composed_by") == "fallback"

    await run_bounded(readers, compose_one, concurrency)
    report.llm_cost_usd = round(report.llm_cost_usd, 6)
    return report


async def compose(settings: Settings, user_email: str | None = None) -> None:
    sessionmaker = get_sessionmaker()
    started = datetime.now(UTC)
    report = ComposeReport()
    status = RunStatus.FAILED
    try:
        async with httpx.AsyncClient(
            timeout=10.0, headers={"User-Agent": settings.user_agent}
        ) as http:
            service = EditionService(
                sessionmaker,
                build_llm(settings, sessionmaker),
                settings.llm_smart_model,
                weather=WeatherService(http),
                guard=BudgetGuard(sessionmaker, settings.llm_daily_budget_usd),
            )
            report = await run_compose(sessionmaker, service, user_email=user_email)
        status = RunStatus.SUCCEEDED
    finally:
        async with sessionmaker() as session:
            session.add(
                PipelineRun(
                    stage="compose",
                    started_at=started,
                    finished_at=datetime.now(UTC),
                    status=status,
                    stats=asdict(report),
                )
            )
            await session.commit()
    log.info("compose_done", **asdict(report), budget_usd=settings.llm_daily_budget_usd)
    if report.readers and not (report.built or report.already_done):
        from app.pipeline import PipelineError  # lazy: pipeline imports this stage

        raise PipelineError(f"no edition could be composed for any of {report.readers} readers")
