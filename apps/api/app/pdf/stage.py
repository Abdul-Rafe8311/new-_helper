"""The `render` pipeline stage: typeset every recent finished edition that has no current PDF."""

from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.db.session import get_sessionmaker
from app.models import Edition, EditionStatus, PipelineRun, RunStatus, User
from app.pdf.service import render_edition
from app.storage import Storage, get_storage

log = structlog.get_logger(__name__)

RECENT_DAYS = 2  # today's edition plus yesterday's, in case a reader's day rolled over late


class RenderFailedError(Exception):
    """At least one edition could not be typeset."""


@dataclass
class RenderReport:
    editions: int = 0
    rendered: int = 0
    unchanged: int = 0
    failed: int = 0


async def run_render(
    sessionmaker: async_sessionmaker[AsyncSession],
    storage: Storage,
    settings: Settings,
    user_email: str | None = None,
    today: date | None = None,
) -> RenderReport:
    since = (today or datetime.now(UTC).date()) - timedelta(days=RECENT_DAYS)
    query = select(Edition.id).where(
        Edition.status == EditionStatus.READY, Edition.edition_date >= since
    )
    if user_email:
        query = query.join(User, User.id == Edition.user_id).where(User.email == user_email)
    async with sessionmaker() as session:
        edition_ids = list((await session.execute(query)).scalars())

    report = RenderReport(editions=len(edition_ids))
    for edition_id in edition_ids:
        # one session per edition: a failure never poisons the ones after it
        async with sessionmaker() as session:
            edition = await session.get(Edition, edition_id)
            if edition is None:
                continue
            try:
                result = await render_edition(session, storage, settings, edition)
                await session.commit()
            except Exception:
                log.exception("render_failed", edition_id=str(edition_id))
                report.failed += 1
                continue
        if result.rendered:
            report.rendered += 1
        else:
            report.unchanged += 1
    return report


async def render(settings: Settings, user_email: str | None = None) -> None:
    sessionmaker = get_sessionmaker()
    started = datetime.now(UTC)
    report = RenderReport()
    status = RunStatus.FAILED
    try:
        report = await run_render(sessionmaker, get_storage(settings), settings, user_email)
        status = RunStatus.FAILED if report.failed else RunStatus.SUCCEEDED
    finally:
        async with sessionmaker() as session:
            session.add(
                PipelineRun(
                    stage="render",
                    started_at=started,
                    finished_at=datetime.now(UTC),
                    status=status,
                    stats=asdict(report),
                )
            )
            await session.commit()
    log.info("render_done", **asdict(report))
    if report.failed:
        raise RenderFailedError(f"{report.failed} of {report.editions} editions failed to render")
