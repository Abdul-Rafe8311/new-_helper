import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.taxonomy import TOPIC_SLUGS
from app.onboarding.suggestions import SUGGESTIONS, suggestions_for
from tests.factories import DEFAULT_PASSWORD, make_user


def test_every_topic_has_suggestions_and_nothing_else_does() -> None:
    assert set(SUGGESTIONS) == TOPIC_SLUGS
    assert all(len(v) >= 4 and len(set(v)) == len(v) for v in SUGGESTIONS.values())


def test_unknown_topic_has_none() -> None:
    assert suggestions_for("nope") is None
    assert suggestions_for("cricket") == list(SUGGESTIONS["cricket"])


async def _login(client: AsyncClient, db: AsyncSession) -> None:
    await make_user(db, email="reader@example.com")
    response = await client.post(
        "/auth/login", json={"email": "reader@example.com", "password": DEFAULT_PASSWORD}
    )
    assert response.status_code == 200


@pytest.mark.integration
async def test_suggestions_endpoint(client: AsyncClient, db: AsyncSession) -> None:
    assert (await client.get("/onboarding/suggestions?topic=cricket")).status_code == 401
    await _login(client, db)
    body = (await client.get("/onboarding/suggestions?topic=cricket")).json()
    assert body["topic"] == "cricket"
    assert {"PSL", "Pakistan team", "Test cricket"} <= set(body["suggestions"])
    missing = await client.get("/onboarding/suggestions?topic=nope")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "unknown_topic"
    assert (await client.get("/onboarding/suggestions")).status_code == 422
