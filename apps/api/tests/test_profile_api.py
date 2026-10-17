import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import DEFAULT_PASSWORD, make_user

pytestmark = pytest.mark.integration


async def _login(client: AsyncClient, db: AsyncSession) -> None:
    await make_user(db, email="reader@example.com")
    response = await client.post(
        "/auth/login", json={"email": "reader@example.com", "password": DEFAULT_PASSWORD}
    )
    assert response.status_code == 200


async def test_profile_requires_session(client: AsyncClient) -> None:
    assert (await client.get("/me/profile")).status_code == 401
    assert (await client.put("/me/profile", json={})).status_code == 401


async def test_get_profile_defaults(client: AsyncClient, db: AsyncSession) -> None:
    await _login(client, db)
    response = await client.get("/me/profile")
    assert response.status_code == 200
    body = response.json()
    assert body["onboarding_completed"] is False
    assert body["topics"] == {}
    assert body["depth"] == "balanced"
    assert body["reading_minutes"] == 15
    assert body["entities"] == {"people": [], "companies": [], "teams": [], "places": []}
    assert "interest_vector" not in body


async def test_put_profile_updates_only_given_fields(client: AsyncClient, db: AsyncSession) -> None:
    await _login(client, db)
    changes = {
        "topics": {"cricket": 1.0, "ai": 0.7},
        "keywords": ["  PSL  "],
        "entities": {"teams": ["Lahore Qalandars"]},
        "depth": "deep",
        "reading_minutes": 25,
        "paper_name": "The Lahore Ledger",
        "onboarding_completed": True,
    }
    response = await client.put("/me/profile", json=changes)
    assert response.status_code == 200
    body = response.json()
    assert body["topics"] == {"cricket": 1.0, "ai": 0.7}
    assert body["keywords"] == ["PSL"]
    assert body["entities"]["teams"] == ["Lahore Qalandars"]
    assert body["depth"] == "deep"
    assert body["surprise_me"] is True  # untouched

    second = await client.put("/me/profile", json={"surprise_me": False, "paper_name": None})
    assert second.json()["paper_name"] is None
    persisted = (await client.get("/me/profile")).json()
    assert persisted["surprise_me"] is False
    assert persisted["topics"] == {"cricket": 1.0, "ai": 0.7}
    assert (await client.get("/auth/me")).json()["onboarding_completed"] is True


@pytest.mark.parametrize(
    "payload",
    [
        {"topics": {"not-a-topic": 0.5}},
        {"topics": {"ai": 1.5}},
        {"reading_minutes": 2},
        {"depth": "epic"},
        {"interest_vector": [0.1]},
    ],
)
async def test_put_profile_validates(
    client: AsyncClient, db: AsyncSession, payload: dict[str, object]
) -> None:
    await _login(client, db)
    response = await client.put("/me/profile", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_stub_routes_require_auth_then_501(client: AsyncClient, db: AsyncSession) -> None:
    assert (await client.get("/editions")).status_code == 401
    await _login(client, db)
    for response in (
        await client.get("/editions"),
        await client.get("/editions/2026-10-17"),
        await client.post("/events"),
    ):
        assert response.status_code == 501
        assert response.json()["error"]["code"] == "not_implemented"
