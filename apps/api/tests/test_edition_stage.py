import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import FakeLLM
from app.editions.service import EditionService
from app.editions.stage import list_readers, run_bounded, run_compose
from app.models import Edition, EditionStatus
from app.pipeline import STAGE_FNS
from tests.editions_helpers import fake_editor, seed_articles, sessionmaker_for
from tests.factories import make_user

NOW = datetime(2026, 10, 17, 22, 0, tzinfo=UTC)  # already Oct 18 in Karachi, still Oct 17 in LA
MODEL = "claude-sonnet-5-5"


def test_compose_is_registered_as_a_pipeline_stage() -> None:
    assert "compose" in STAGE_FNS


async def test_run_bounded_limits_concurrency_and_survives_failures() -> None:
    running = peak = done = 0

    async def work(n: int) -> None:
        nonlocal running, peak, done
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(0.01)
        running -= 1
        if n == 3:
            raise RuntimeError("one reader blows up")
        done += 1

    await run_bounded(range(20), work, limit=5)
    assert peak == 5
    assert done == 19


async def onboarded(db: AsyncSession, email: str, tz: str, done: bool = True) -> None:
    await make_user(
        db,
        email=email,
        timezone=tz,
        profile={"onboarding_completed": done, "topics": {"ai": 0.9}, "reading_minutes": 10},
    )


@pytest.mark.integration
async def test_only_onboarded_readers_are_listed_and_email_filters(db: AsyncSession) -> None:
    await onboarded(db, "a@example.com", "Asia/Karachi")
    await onboarded(db, "b@example.com", "UTC")
    await onboarded(db, "new@example.com", "UTC", done=False)
    assert len(await list_readers(db)) == 2
    only = await list_readers(db, " A@Example.com ")
    assert len(only) == 1
    assert only[0].timezone == "Asia/Karachi"


@pytest.mark.integration
async def test_compose_builds_one_paper_per_reader_dated_in_their_timezone(
    db: AsyncSession,
) -> None:
    await seed_articles(db, "ai", "Agents", now=NOW)
    await onboarded(db, "karachi@example.com", "Asia/Karachi")
    await onboarded(db, "la@example.com", "America/Los_Angeles")
    await onboarded(db, "new@example.com", "UTC", done=False)
    sm = sessionmaker_for(db)
    llm = fake_editor(cost=0.02)
    service = EditionService(sm, llm, MODEL, clock=lambda: NOW)

    report = await run_compose(sm, service, now=NOW, concurrency=1)

    assert (report.readers, report.built, report.failed, report.already_done) == (2, 2, 0, 0)
    assert report.llm_calls == 2
    assert report.llm_cost_usd == pytest.approx(0.04)
    assert report.items > 0
    assert report.fallback_layouts == 0
    editions = (await db.scalars(select(Edition))).all()
    assert sorted(e.edition_date.isoformat() for e in editions) == ["2026-10-17", "2026-10-18"]
    assert all(e.status is EditionStatus.READY for e in editions)

    again = await run_compose(sm, service, now=NOW, concurrency=1)
    assert (again.built, again.already_done) == (0, 2)
    assert len(llm.calls) == 2  # idempotent: a second run costs nothing


@pytest.mark.integration
async def test_a_failing_reader_is_counted_and_does_not_stop_the_others(
    db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed_articles(db, "ai", "Agents", now=NOW)
    await onboarded(db, "a@example.com", "UTC")
    await onboarded(db, "b@example.com", "UTC")
    sm = sessionmaker_for(db)
    service = EditionService(sm, fake_editor(), MODEL, clock=lambda: NOW)
    real_build = EditionService.build
    calls = 0

    async def flaky(self: EditionService, session: AsyncSession, edition_id: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("database hiccup")
        await real_build(self, session, edition_id)  # type: ignore[arg-type]

    monkeypatch.setattr(EditionService, "build", flaky)
    report = await run_compose(sm, service, now=NOW, concurrency=1)
    assert (report.built, report.failed) == (1, 1)


@pytest.mark.integration
async def test_readers_without_articles_fail_and_template_papers_are_counted(
    db: AsyncSession,
) -> None:
    await onboarded(db, "a@example.com", "UTC")
    sm = sessionmaker_for(db)
    service = EditionService(sm, FakeLLM([]), MODEL, clock=lambda: NOW)
    report = await run_compose(sm, service, now=NOW, concurrency=1)
    assert (report.built, report.failed) == (0, 1)
    await seed_articles(db, "ai", "Agents", now=NOW + timedelta(seconds=0))
    retry = await run_compose(sm, service, now=NOW, concurrency=1)
    assert (retry.built, retry.fallback_layouts) == (1, 1)  # the FakeLLM has no replies: template
