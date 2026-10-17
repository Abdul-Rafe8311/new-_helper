"""The `learn` pipeline stage: update each reader's profile from their behaviour."""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy import select

from app.core.config import Settings
from app.db.session import get_sessionmaker
from app.models import PipelineRun, ReaderProfile, RunStatus, User
from app.personalize.learn_service import learn_reader

log = structlog.get_logger(__name__)


@dataclass
class LearnReport:
    readers: int = 0
    learned: int = 0
    changes: int = 0
    failed: int = 0


async def learn(settings: Settings, user_email: str | None = None) -> None:
    """One nightly learner run per onboarded reader; one reader failing never stops the rest."""
    sessionmaker = get_sessionmaker()
    started = datetime.now(UTC)
    report = LearnReport()
    status = RunStatus.FAILED
    try:
        stmt = (
            select(User.id)
            .join(ReaderProfile, ReaderProfile.user_id == User.id)
            .where(ReaderProfile.onboarding_completed.is_(True))
            .order_by(User.email)
        )
        if user_email:
            stmt = stmt.where(User.email == user_email.strip().lower())
        async with sessionmaker() as session:
            reader_ids: list[UUID] = list((await session.execute(stmt)).scalars().all())
        report.readers = len(reader_ids)
        for user_id in reader_ids:
            try:
                async with sessionmaker() as session:
                    changes = await learn_reader(session, user_id, nightly=True)
            except Exception:
                report.failed += 1
                log.exception("learn_reader_crashed", user_id=str(user_id))
                continue
            report.learned += 1
            report.changes += len(changes)
        status = RunStatus.SUCCEEDED
    finally:
        async with sessionmaker() as session:
            session.add(
                PipelineRun(
                    stage="learn",
                    started_at=started,
                    finished_at=datetime.now(UTC),
                    status=status,
                    stats=asdict(report),
                )
            )
            await session.commit()
    log.info("learn_done", **asdict(report))
