import asyncio
import io
import time
from datetime import date, timedelta
from uuid import UUID, uuid4

import pytest
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models import Edition, EditionStatus
from app.pdf.service import (
    EditionNotReadyError,
    load_snapshot,
    pdf_filename,
    pdf_path,
    render_edition,
)
from app.pdf.stage import RECENT_DAYS, run_render
from app.storage import LocalStorage
from tests.factories import make_user
from tests.pdf_helpers import fixture_snapshot, make_fixture_edition

pytestmark = pytest.mark.integration


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(tmp_path / "files")


@pytest.fixture
def settings(tmp_path):
    return Settings(env="test", storage_local_dir=str(tmp_path / "files"))


async def reader_edition(db: AsyncSession, **profile):
    user = await make_user(
        db,
        display_name="Rafe",
        city="Islamabad",
        profile={"paper_name": "The Rafe Courier", **profile},
    )
    return user, await make_fixture_edition(db, user)


def test_paths_and_filenames():
    uid = UUID("12345678-1234-5678-1234-567812345678")
    assert pdf_path(uid, date(2026, 10, 17)) == f"editions/{uid}/2026-10-17.pdf"
    assert pdf_filename("The Rafe Courier", date(2026, 10, 17)) == "the-rafe-courier-2026-10-17.pdf"
    assert pdf_filename("Café Dawn!", date(2026, 10, 17)) == "cafe-dawn-2026-10-17.pdf"
    assert pdf_filename("???", date(2026, 10, 17)) == "newshelper-2026-10-17.pdf"


async def test_snapshot_comes_from_the_database_records(db, settings):
    _, edition = await reader_edition(db, depth="deep", topics={"pakistan": 1.0})
    snapshot = await load_snapshot(db, edition, settings)
    assert snapshot.paper_name == "The Rafe Courier"
    assert snapshot.reader_name == "Rafe"
    assert snapshot.depth == "deep"
    assert snapshot.reader_topics == {"pakistan": 1.0}
    assert len(snapshot.stories) == 27
    assert snapshot.story(snapshot.lead_item_id).source_name == "Financial Times"


async def test_render_stores_the_pdf_and_skips_when_unchanged(db, storage, settings):
    user, edition = await reader_edition(db)
    first = await render_edition(db, storage, settings, edition)
    assert first.rendered
    assert first.path == pdf_path(user.id, edition.edition_date)
    assert edition.pdf_path == first.path
    assert edition.pdf_hash
    pdf = await storage.get(first.path)
    assert len(PdfReader(io.BytesIO(pdf)).pages) >= 2

    again = await render_edition(db, storage, settings, edition)
    assert not again.rendered  # same content, same file


async def test_render_runs_again_when_the_edition_or_file_changed(db, storage, settings):
    _, edition = await reader_edition(db)
    first = await render_edition(db, storage, settings, edition)
    edition.editor_note = "A new note written after the first render."
    assert (await render_edition(db, storage, settings, edition)).rendered

    stored_hash = edition.pdf_hash
    assert (await render_edition(db, storage, settings, edition, force=True)).rendered
    assert edition.pdf_hash == stored_hash

    (storage.root / first.path).unlink()
    assert (await render_edition(db, storage, settings, edition)).rendered  # file went missing


async def test_unfinished_editions_are_not_typeset(db, storage, settings):
    user = await make_user(db)
    edition = await make_fixture_edition(db, user, status=EditionStatus.PENDING)
    with pytest.raises(EditionNotReadyError):
        await render_edition(db, storage, settings, edition)


class _Sessions:
    """A sessionmaker stand-in that hands out the test's rolled-back session."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def __call__(self) -> "_Sessions":
        return self

    async def __aenter__(self) -> AsyncSession:
        return self.session

    async def __aexit__(self, *exc: object) -> bool:
        return False


FIXTURE_DAY = date(2026, 10, 17)


async def test_stage_renders_recent_ready_editions_and_is_idempotent(db, storage, settings):
    _, ready = await reader_edition(db)
    pending_owner = await make_user(db, email="pending@example.com")
    pending = await make_fixture_edition(db, pending_owner, status=EditionStatus.PENDING)
    sessions = _Sessions(db)

    first = await run_render(sessions, storage, settings, today=FIXTURE_DAY)  # type: ignore[arg-type]
    assert (first.editions, first.rendered, first.unchanged, first.failed) == (1, 1, 0, 0)
    assert ready.pdf_path
    assert pending.pdf_path is None

    second = await run_render(sessions, storage, settings, today=FIXTURE_DAY)  # type: ignore[arg-type]
    assert (second.rendered, second.unchanged) == (0, 1)

    later = FIXTURE_DAY + timedelta(days=RECENT_DAYS + 1)
    assert (await run_render(sessions, storage, settings, today=later)).editions == 0  # type: ignore[arg-type]


async def test_stage_can_be_limited_to_one_reader(db, storage, settings):
    await make_fixture_edition(db, await make_user(db, email="a@example.com"))
    sessions = _Sessions(db)
    report = await run_render(
        sessions,  # type: ignore[arg-type]
        storage,
        settings,
        user_email="nobody@example.com",
        today=FIXTURE_DAY,
    )
    assert report.editions == 0


async def test_one_failing_edition_does_not_stop_the_rest(db, storage, settings, monkeypatch):
    _, first = await reader_edition(db)
    await make_user(db, email="second@example.com")
    real = render_edition
    calls: list[str] = []

    async def flaky(session, store, conf, edition, **kwargs):
        calls.append(str(edition.id))
        if len(calls) == 1:
            raise RuntimeError("typesetting exploded")
        return await real(session, store, conf, edition, **kwargs)

    monkeypatch.setattr("app.pdf.stage.render_edition", flaky)
    report = await run_render(_Sessions(db), storage, settings, today=FIXTURE_DAY)  # type: ignore[arg-type]
    assert (report.editions, report.failed) == (1, 1)
    assert first.pdf_path is None


async def test_renders_run_one_at_a_time(storage, settings, monkeypatch):
    """The API has 512 MB: two requests must not typeset side by side."""
    running = peak = 0

    def slow_render(snapshot, images):
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        time.sleep(0.05)
        running -= 1
        return b"%PDF-fake"

    async def fixture_snapshot_for(session, edition, conf):
        return fixture_snapshot()

    monkeypatch.setattr("app.pdf.service.render_pdf", slow_render)
    monkeypatch.setattr("app.pdf.service.load_snapshot", fixture_snapshot_for)
    editions = [
        Edition(id=uuid4(), user_id=uuid4(), edition_date=FIXTURE_DAY, number=1, status="ready")
        for _ in range(2)
    ]
    for edition in editions:
        edition.status = EditionStatus.READY
    await asyncio.gather(*(render_edition(None, storage, settings, e) for e in editions))  # type: ignore[arg-type]
    assert peak == 1
