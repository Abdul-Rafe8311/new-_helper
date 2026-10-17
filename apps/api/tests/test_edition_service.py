from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import FakeLLM
from app.core.errors import AppError
from app.editions.service import (
    MAX_REGENERATIONS_PER_DAY,
    STALE_PENDING,
    EditionService,
    assign_slot,
    local_date,
)
from app.editions.weather import Weather
from app.models import Edition, EditionItem, EditionStatus, Slot
from app.models.enums import Depth
from tests.editions_helpers import (
    NOW,
    E,
    StubWeather,
    fake_editor,
    reader,
    seed_articles,
    sessionmaker_for,
)
from tests.personalize_helpers import selection

TODAY = NOW.date()
MODEL = "claude-sonnet-5-5"


def service(
    db: AsyncSession,
    llm: FakeLLM | None,
    *,
    weather: StubWeather | None = None,
    now: datetime = NOW,
) -> EditionService:
    return EditionService(sessionmaker_for(db), llm, MODEL, weather=weather, clock=lambda: now)


@pytest.mark.integration
async def test_generates_a_ready_edition_with_items_layout_and_stats(db: AsyncSession) -> None:
    articles = await seed_articles(db, "ai", "Agents")
    user = await reader(db, topics={"ai": 0.9}, interest_vector=E.embed(["Agents story 0"])[0])
    llm = fake_editor(cost=0.0123)
    weather = Weather(city="Lahore", condition="Clear", temp_max_c=31, temp_min_c=18)
    edition = await service(db, llm, weather=StubWeather(weather)).generate_edition(
        db, user.id, TODAY
    )

    assert edition.status is EditionStatus.READY
    assert edition.number == 1
    assert edition.title == "The Fake Morning"
    assert edition.editor_note == "Good morning. Here is your paper."
    assert edition.generated_at == NOW
    items = (
        await db.scalars(
            select(EditionItem)
            .where(EditionItem.edition_id == edition.id)
            .order_by(EditionItem.position)
        )
    ).all()
    assert len(items) == 12  # fewer articles than the 14 slots a 10-minute paper allows
    assert [i.position for i in items] == list(range(12))
    assert {i.article_id for i in items} <= {a.id for a in articles}
    assert all(i.why_text and (i.headline or "").startswith("Rewritten") for i in items)
    assert all(set(i.score_breakdown["components"]) >= {"semantic", "topic"} for i in items)
    assert sum(i.slot is Slot.LEAD for i in items) == 1

    layout = edition.layout
    item_ids = {str(i.id) for i in items}
    assert layout["lead_item_id"] in item_ids
    assert [s["name"] for s in layout["sections"]] == ["Fake Section One", "Fake Section Two"]
    assert {i for s in layout["sections"] for i in s["item_ids"]} == item_ids
    assert layout["quote"]["item_id"] in item_ids
    assert len(layout["quiz"]) == 3
    assert layout["masthead"]["weather"]["condition"] == "Clear"
    assert layout["composed_by"] == "llm"

    stats = edition.stats
    assert stats["items"] == 12
    assert stats["sources"] == 6
    assert stats["topics"] == 1
    assert stats["llm_calls"] == 1
    assert stats["llm_cost_usd"] == pytest.approx(0.0123, abs=1e-6)
    assert stats["composed_by"] == "llm"
    assert stats["regenerations"] == 0
    assert stats["stage"] == "done"


@pytest.mark.integration
async def test_generation_is_idempotent_per_user_and_date(db: AsyncSession) -> None:
    await seed_articles(db, "ai", "Agents")
    user = await reader(db, topics={"ai": 0.9})
    llm = fake_editor()
    svc = service(db, llm)
    first = await svc.generate_edition(db, user.id, TODAY)
    again = await svc.generate_edition(db, user.id, TODAY)
    assert again.id == first.id
    assert len(llm.calls) == 1
    count = await db.scalar(select(func.count()).select_from(EditionItem))
    assert count == first.stats["items"]
    editions = await db.scalar(select(func.count()).select_from(Edition))
    assert editions == 1


@pytest.mark.integration
async def test_force_regenerates_in_place_up_to_three_times(db: AsyncSession) -> None:
    await seed_articles(db, "ai", "Agents")
    user = await reader(db, topics={"ai": 0.9})
    llm = fake_editor()
    svc = service(db, llm)
    first = await svc.generate_edition(db, user.id, TODAY)
    for n in range(1, MAX_REGENERATIONS_PER_DAY + 1):
        again = await svc.generate_edition(db, user.id, TODAY, force=True)
        assert again.id == first.id
        assert again.number == 1
        assert again.stats["regenerations"] == n
    assert len(llm.calls) == 1 + MAX_REGENERATIONS_PER_DAY
    with pytest.raises(AppError) as err:
        await svc.generate_edition(db, user.id, TODAY, force=True)
    assert err.value.status_code == 429
    total = await db.scalar(select(func.count()).select_from(EditionItem))
    assert total == first.stats["items"]  # replaced, not stacked


@pytest.mark.integration
async def test_next_day_gets_the_next_number_and_does_not_repeat_stories(db: AsyncSession) -> None:
    await seed_articles(db, "ai", "Agents", count=28)
    user = await reader(db, topics={"ai": 0.9}, interest_vector=E.embed(["Agents story 0"])[0])
    svc = service(db, fake_editor())
    one = await svc.generate_edition(db, user.id, TODAY)
    two = await svc.generate_edition(db, user.id, TODAY + timedelta(days=1))
    assert (one.number, two.number) == (1, 2)
    rows = (await db.execute(select(EditionItem.edition_id, EditionItem.article_id))).all()
    first = {a for e, a in rows if e == one.id}
    second = {a for e, a in rows if e == two.id}
    assert first
    assert second
    assert not first & second


@pytest.mark.integration
async def test_llm_failure_still_prints_a_template_paper(db: AsyncSession) -> None:
    await seed_articles(db, "ai", "Agents")
    user = await reader(db, topics={"ai": 0.9})
    edition = await service(db, FakeLLM([])).generate_edition(db, user.id, TODAY)
    assert edition.status is EditionStatus.READY
    assert edition.layout["composed_by"] == "fallback"
    assert edition.layout["fallback_reason"] == "llm_error: LLMError"
    assert edition.stats["composed_by"] == "fallback"
    assert edition.title == "The Sara Morning"


@pytest.mark.integration
async def test_without_an_llm_or_budget_the_template_is_used(db: AsyncSession) -> None:
    await seed_articles(db, "ai", "Agents")
    user = await reader(db, topics={"ai": 0.9}, paper_name="The Sara Paper")
    edition = await service(db, None).generate_edition(db, user.id, TODAY)
    assert edition.status is EditionStatus.READY
    assert edition.title == "The Sara Paper"
    assert edition.layout["fallback_reason"] == "no_llm"
    assert edition.stats["llm_calls"] == 0


@pytest.mark.integration
async def test_no_articles_fails_the_edition_and_a_later_run_recovers(db: AsyncSession) -> None:
    user_id = (await reader(db, topics={"ai": 0.9})).id  # a rollback expires ORM objects
    svc = service(db, fake_editor())
    failed = await svc.generate_edition(db, user_id, TODAY)
    assert failed.status is EditionStatus.FAILED
    assert "NoArticlesError" in failed.stats["error"]
    await seed_articles(db, "ai", "Agents")
    recovered = await svc.generate_edition(db, user_id, TODAY)
    assert recovered.id == failed.id
    assert recovered.status is EditionStatus.READY


@pytest.mark.integration
async def test_pending_editions_are_left_alone_until_stale(db: AsyncSession) -> None:
    await seed_articles(db, "ai", "Agents")
    user = await reader(db, topics={"ai": 0.9})
    svc = service(db, fake_editor())
    prepared = await svc.prepare(db, user.id, TODAY)
    assert prepared.needs_build
    again = await svc.prepare(db, user.id, TODAY)
    assert (again.edition.id, again.needs_build) == (prepared.edition.id, False)
    later = service(
        db, fake_editor(), now=prepared.edition.updated_at + STALE_PENDING + timedelta(minutes=1)
    )
    assert (await later.prepare(db, user.id, TODAY)).needs_build


@pytest.mark.integration
async def test_losing_the_reservation_race_returns_the_winners_edition(
    db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = await reader(db)
    svc = service(db, fake_editor())
    winner = (await svc.prepare(db, user.id, TODAY)).edition
    real = EditionService._existing
    calls = 0

    async def blind_once(session: AsyncSession, user_id: Any, day: date) -> Edition | None:
        nonlocal calls
        calls += 1
        return None if calls == 1 else await real(session, user_id, day)

    monkeypatch.setattr(EditionService, "_existing", staticmethod(blind_once))
    lost = await svc.prepare(db, user.id, TODAY)
    assert lost.edition.id == winner.id
    assert lost.needs_build is False


@pytest.mark.integration
async def test_unique_constraint_guards_user_and_date(db: AsyncSession) -> None:
    user = await reader(db)
    db.add(Edition(user_id=user.id, edition_date=TODAY, number=1))
    await db.flush()
    with pytest.raises(IntegrityError):
        async with db.begin_nested():
            db.add(Edition(user_id=user.id, edition_date=TODAY, number=2))


@pytest.mark.integration
async def test_two_readers_get_clearly_different_papers(db: AsyncSession) -> None:
    ai = await seed_articles(db, "ai", "Agents", count=14)
    cricket = await seed_articles(db, "cricket", "Wickets", count=14)
    fan = await reader(
        db,
        topics={"ai": 0.9, "startups": 0.5},
        keywords=["Agents"],
        interest_vector=E.embed(["Agents story 0"])[0],
        surprise_me=False,
    )
    fielder = await reader(
        db,
        topics={"cricket": 0.9},
        keywords=["Wickets"],
        interest_vector=E.embed(["Wickets story 0"])[0],
        surprise_me=False,
    )
    svc = service(db, fake_editor())
    a = await svc.generate_edition(db, fan.id, TODAY)
    b = await svc.generate_edition(db, fielder.id, TODAY)
    rows = (await db.execute(select(EditionItem.edition_id, EditionItem.article_id))).all()
    a_ids = {x for e, x in rows if e == a.id}
    b_ids = {x for e, x in rows if e == b.id}
    ai_ids, cricket_ids = {x.id for x in ai}, {x.id for x in cricket}
    assert len(a_ids & ai_ids) > len(a_ids & cricket_ids)
    assert len(b_ids & cricket_ids) > len(b_ids & ai_ids)
    assert len(a_ids & b_ids) <= 4


@pytest.mark.integration
async def test_explore_items_appear_only_when_surprise_me_is_on(db: AsyncSession) -> None:
    await seed_articles(db, "ai", "Agents", count=14)
    await seed_articles(db, "space", "Rockets", count=6)
    kwargs: dict[str, Any] = {
        "topics": {"ai": 0.9},
        "interest_vector": E.embed(["Agents story 0"])[0],
    }
    on = await reader(db, surprise_me=True, **kwargs)
    off = await reader(db, surprise_me=False, **kwargs)
    svc = service(db, fake_editor())
    ed_on = await svc.generate_edition(db, on.id, TODAY)
    ed_off = await svc.generate_edition(db, off.id, TODAY)
    slots = (await db.execute(select(EditionItem.edition_id, EditionItem.slot))).all()
    assert sum(s is Slot.EXPLORE for e, s in slots if e == ed_on.id) == 2
    assert sum(s is Slot.EXPLORE for e, s in slots if e == ed_off.id) == 0
    assert ed_on.stats["explore_items"] == 2


def test_local_date_uses_the_readers_timezone() -> None:
    late = datetime(2026, 10, 17, 22, 0, tzinfo=UTC)
    assert local_date("Asia/Karachi", late) == date(2026, 10, 18)
    assert local_date("America/Los_Angeles", late) == date(2026, 10, 17)
    assert local_date("Not/AZone", late) == date(2026, 10, 17)


def test_assign_slot() -> None:
    plain, explore = selection(), selection(explore=True)
    assert (
        assign_slot(plain, is_lead=True, first_in_section=True, depth=Depth.BALANCED) is Slot.LEAD
    )
    assert (
        assign_slot(explore, is_lead=False, first_in_section=True, depth=Depth.BALANCED)
        is Slot.EXPLORE
    )
    assert (
        assign_slot(plain, is_lead=False, first_in_section=True, depth=Depth.BALANCED)
        is Slot.FEATURE
    )
    assert (
        assign_slot(plain, is_lead=False, first_in_section=False, depth=Depth.DEEP) is Slot.STANDARD
    )
    assert assign_slot(plain, is_lead=False, first_in_section=True, depth=Depth.BRIEF) is Slot.BRIEF
