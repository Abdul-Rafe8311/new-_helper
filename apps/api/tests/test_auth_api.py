import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import SESSION_COOKIE
from app.scripts.seed import seed_demo_user
from tests.conftest import TEST_SETTINGS
from tests.factories import DEFAULT_PASSWORD, make_user

pytestmark = pytest.mark.integration

NEW_READER = {"email": "Ada@Example.com", "password": "s3cret-pass", "display_name": "Ada"}


async def test_register_sets_session_cookie(client: AsyncClient) -> None:
    response = await client.post("/auth/register", json=NEW_READER)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ada@example.com"
    assert body["onboarding_completed"] is False
    set_cookie = response.headers["set-cookie"]
    assert set_cookie.startswith(f"{SESSION_COOKIE}=")
    assert "HttpOnly" in set_cookie
    assert "samesite=lax" in set_cookie.lower()
    assert "Max-Age=604800" in set_cookie

    me = await client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["id"] == body["id"]


async def test_register_rejects_duplicate_email(client: AsyncClient, db: AsyncSession) -> None:
    await make_user(db, email="ada@example.com")
    response = await client.post("/auth/register", json=NEW_READER)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"


async def test_register_validates_input(client: AsyncClient) -> None:
    response = await client.post("/auth/register", json={**NEW_READER, "password": "short"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    bad_email = await client.post("/auth/register", json={**NEW_READER, "email": "nope"})
    assert bad_email.status_code == 422


async def test_login_success(client: AsyncClient, db: AsyncSession) -> None:
    user = await make_user(db, email="grace@example.com")
    response = await client.post(
        "/auth/login", json={"email": "GRACE@example.com", "password": DEFAULT_PASSWORD}
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)
    assert SESSION_COOKIE in response.cookies
    assert (await client.get("/auth/me")).status_code == 200


@pytest.mark.parametrize(
    ("email", "password"),
    [("grace@example.com", "wrong-password"), ("nobody@example.com", DEFAULT_PASSWORD)],
)
async def test_login_rejects_bad_credentials(
    client: AsyncClient, db: AsyncSession, email: str, password: str
) -> None:
    await make_user(db, email="grace@example.com")
    response = await client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"
    assert SESSION_COOKIE not in response.cookies


async def test_me_requires_session(client: AsyncClient) -> None:
    response = await client.get("/auth/me")
    assert response.status_code == 401
    assert response.json() == {
        "error": {"code": "not_authenticated", "message": "Sign in to continue"}
    }
    client.cookies.set(SESSION_COOKIE, "garbage")
    assert (await client.get("/auth/me")).status_code == 401


async def test_logout_clears_session(client: AsyncClient) -> None:
    await client.post("/auth/register", json=NEW_READER)
    response = await client.post("/auth/logout")
    assert response.status_code == 204
    assert f'{SESSION_COOKIE}=""' in response.headers["set-cookie"]
    assert (await client.get("/auth/me")).status_code == 401


async def test_demo_login(client: AsyncClient, db: AsyncSession) -> None:
    missing = await client.post("/auth/demo")
    assert missing.status_code == 503
    assert missing.json()["error"]["code"] == "demo_unavailable"

    assert await seed_demo_user(db, TEST_SETTINGS) is True
    response = await client.post("/auth/demo")
    assert response.status_code == 200
    assert response.json()["email"] == TEST_SETTINGS.demo_email
    assert response.json()["onboarding_completed"] is True
    me = await client.get("/auth/me")
    assert me.json()["email"] == TEST_SETTINGS.demo_email
