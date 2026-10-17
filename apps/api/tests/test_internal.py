from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

SECRET = "c" * 64


def _client() -> TestClient:
    return TestClient(create_app(Settings(env="test", cron_secret=SECRET)))


def test_internal_requires_cron_secret() -> None:
    client = _client()
    missing = client.get("/internal/ping")
    assert missing.status_code == 403
    assert missing.json()["error"]["code"] == "forbidden"
    wrong = client.get("/internal/ping", headers={"X-Cron-Secret": "nope"})
    assert wrong.status_code == 403


def test_internal_accepts_cron_secret() -> None:
    response = _client().get("/internal/ping", headers={"X-Cron-Secret": SECRET})
    assert response.status_code == 200
    assert response.json() == {"ok": True}
