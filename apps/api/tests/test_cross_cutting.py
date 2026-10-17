from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import AppError, register_error_handlers
from app.core.middleware import RequestIDMiddleware
from app.main import app, create_app


def _client() -> TestClient:
    probe = FastAPI()
    register_error_handlers(probe)
    probe.add_middleware(RequestIDMiddleware)

    @probe.get("/app-error")
    async def app_error() -> None:
        raise AppError(409, "email_taken", "Taken")

    @probe.get("/boom")
    async def boom() -> None:
        raise RuntimeError("kaput")

    @probe.get("/items/{n}")
    async def item(n: int) -> dict[str, int]:
        return {"n": n}

    return TestClient(probe, raise_server_exceptions=False)


def test_not_found_uses_error_shape() -> None:
    response = TestClient(app).get("/nope")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Not Found"}}


def test_app_error_shape() -> None:
    response = _client().get("/app-error")
    assert response.status_code == 409
    assert response.json() == {"error": {"code": "email_taken", "message": "Taken"}}


def test_validation_error_shape() -> None:
    response = _client().get("/items/abc")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "n" in response.json()["error"]["message"]


def test_unhandled_error_hides_details() -> None:
    response = _client().get("/boom")
    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "Something went wrong"}
    }


def test_request_id_generated_and_echoed() -> None:
    client = TestClient(app)
    generated = client.get("/health").headers["X-Request-ID"]
    assert len(generated) == 32
    echoed = client.get("/health", headers={"X-Request-ID": "abc-123"}).headers["X-Request-ID"]
    assert echoed == "abc-123"
    sanitised = client.get("/health", headers={"X-Request-ID": "bad id\n"}).headers["X-Request-ID"]
    assert sanitised != "bad id\n"


PREFLIGHT = {"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"}


def test_cors_allows_local_web_in_dev() -> None:
    client = TestClient(create_app(Settings(env="dev", cors_origins=["http://localhost:3000"])))
    response = client.options("/health", headers=PREFLIGHT)
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_disabled_outside_dev() -> None:
    client = TestClient(create_app(Settings(env="prod")))
    response = client.options("/health", headers=PREFLIGHT)
    assert "access-control-allow-origin" not in response.headers
