import io

import pytest
from httpx import AsyncClient
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routers.editions import get_storage_dep
from app.models import EditionStatus, EventType, ReaderEvent
from app.storage import LocalStorage
from tests.factories import DEFAULT_PASSWORD, make_user
from tests.pdf_helpers import make_fixture_edition

pytestmark = pytest.mark.integration

DAY = "2026-10-17"


@pytest.fixture(autouse=True)
def local_storage(api, tmp_path):
    storage = LocalStorage(tmp_path / "files")
    api.dependency_overrides[get_storage_dep] = lambda: storage
    return storage


async def login(client: AsyncClient, db: AsyncSession, email: str = "rafe@example.com"):
    user = await make_user(
        db, email=email, display_name="Rafe", profile={"paper_name": "The Rafe Courier"}
    )
    response = await client.post("/auth/login", json={"email": email, "password": DEFAULT_PASSWORD})
    assert response.status_code == 200
    return user


async def test_pdf_requires_a_session(client: AsyncClient):
    assert (await client.get(f"/editions/{DAY}/pdf")).status_code == 401


async def test_pdf_streams_with_filename_and_logs_the_download(
    client: AsyncClient, db: AsyncSession, local_storage
):
    user = await login(client, db)
    edition = await make_fixture_edition(db, user)

    response = await client.get(f"/editions/{DAY}/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert (
        response.headers["content-disposition"]
        == 'attachment; filename="the-rafe-courier-2026-10-17.pdf"'
    )
    assert len(PdfReader(io.BytesIO(response.content)).pages) >= 2
    assert await local_storage.exists(f"editions/{user.id}/{DAY}.pdf")  # typeset on first request

    events = (await db.execute(select(ReaderEvent))).scalars().all()
    assert [(e.type, e.user_id, e.edition_id) for e in events] == [
        (EventType.PDF_DOWNLOAD, user.id, edition.id)
    ]
    assert events[0].meta["rendered_now"] is True

    await client.get(f"/editions/{DAY}/pdf")  # second download reuses the stored file
    events = (
        (await db.execute(select(ReaderEvent).order_by(ReaderEvent.created_at))).scalars().all()
    )
    assert len(events) == 2
    assert events[-1].meta["rendered_now"] is False


async def test_pdf_404_when_no_finished_edition(client: AsyncClient, db: AsyncSession):
    user = await login(client, db)
    assert (await client.get(f"/editions/{DAY}/pdf")).status_code == 404
    edition = await make_fixture_edition(db, user, status=EditionStatus.PENDING)
    response = await client.get(f"/editions/{edition.edition_date}/pdf")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_a_reader_cannot_download_someone_elses_paper(client: AsyncClient, db: AsyncSession):
    await login(client, db)
    other = await make_user(db, email="other@example.com")
    await make_fixture_edition(db, other)
    assert (await client.get(f"/editions/{DAY}/pdf")).status_code == 404


async def test_bad_date_is_a_validation_error(client: AsyncClient, db: AsyncSession):
    await login(client, db)
    assert (await client.get("/editions/not-a-date/pdf")).status_code == 422
