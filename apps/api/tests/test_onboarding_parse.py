from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import FakeLLM, LLMError
from app.api.deps import get_llm
from app.core.config import Settings
from app.main import create_app
from app.onboarding.parse import normalise, parse_interests
from tests.conftest import TEST_SETTINGS
from tests.factories import DEFAULT_PASSWORD, make_user

REPLY: dict[str, Any] = {
    "topics": [
        {"slug": "ai", "weight": 0.95},
        {"slug": "cricket", "weight": 0.7},
        {"slug": "f1", "weight": 0.2},
        {"slug": "not-a-topic", "weight": 0.9},
        {"slug": "film-tv", "weight": 0.9},
    ],
    "keywords": ["AI agents", "ai agents", "PSL", "celebrity gossip"],
    "entities": {"companies": ["Anthropic"], "teams": ["Lahore Qalandars"]},
    "blocked": {"topics": ["film-tv", "bogus"], "keywords": ["Celebrity gossip"]},
    "context": " I run a digital agency. ",
}


def test_normalise_clamps_filters_and_honours_blocks() -> None:
    from app.onboarding.parse import _LLMResult

    parsed = normalise(_LLMResult.model_validate(REPLY))
    assert {t.slug: t.weight for t in parsed.topics} == {"ai": 0.9, "cricket": 0.7, "f1": 0.6}
    assert parsed.keywords == ["AI agents", "PSL"]
    assert parsed.blocked.topics == ["film-tv"]
    assert parsed.blocked.keywords == ["Celebrity gossip"]
    assert parsed.entities.teams == ["Lahore Qalandars"]
    assert parsed.context == "I run a digital agency."


async def test_parse_interests_uses_the_fast_model_and_fences_the_text() -> None:
    llm = FakeLLM(replies=[REPLY])
    await parse_interests(llm, "  follow AI agents  ", "claude-haiku-5-5")
    call = llm.calls[0]
    assert call["model"] == "claude-haiku-5-5"
    assert call["purpose"] == "onboarding_parse"
    assert "<reader_text>\nfollow AI agents\n</reader_text>" in call["prompt"]
    assert "cricket:" in call["system"]


@pytest.fixture
async def llm_client(client: AsyncClient, api: FastAPI, db: AsyncSession) -> FakeLLM:
    llm = FakeLLM(replies=[REPLY])
    api.dependency_overrides[get_llm] = lambda: llm
    await make_user(db, email="reader@example.com")
    login = await client.post(
        "/auth/login", json={"email": "reader@example.com", "password": DEFAULT_PASSWORD}
    )
    assert login.status_code == 200
    return llm


@pytest.mark.integration
async def test_parse_endpoint(client: AsyncClient, llm_client: FakeLLM) -> None:
    response = await client.post("/onboarding/parse", json={"text": "AI agents, cricket, F1"})
    assert response.status_code == 200
    body = response.json()
    assert body["topics"][0] == {"slug": "ai", "weight": 0.9}
    assert body["blocked"]["topics"] == ["film-tv"]
    assert body["context"] == "I run a digital agency."
    assert llm_client.calls[0]["model"] == TEST_SETTINGS.llm_fast_model


@pytest.mark.integration
async def test_parse_validates_input(client: AsyncClient, llm_client: FakeLLM) -> None:
    assert (await client.post("/onboarding/parse", json={"text": "  "})).status_code == 422
    assert (await client.post("/onboarding/parse", json={"text": "x" * 1501})).status_code == 422
    assert llm_client.calls == []


@pytest.mark.integration
async def test_parse_requires_session(client: AsyncClient) -> None:
    assert (await client.post("/onboarding/parse", json={"text": "cricket"})).status_code == 401


@pytest.mark.integration
async def test_parse_reports_llm_failure(
    client: AsyncClient, api: FastAPI, llm_client: FakeLLM
) -> None:
    class Failing(FakeLLM):
        async def complete_json(self, *args: Any, **kwargs: Any) -> Any:
            raise LLMError("boom")

    api.dependency_overrides[get_llm] = lambda: Failing()
    response = await client.post("/onboarding/parse", json={"text": "cricket"})
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "llm_failed"


async def test_get_llm_needs_a_key() -> None:
    from app.core.errors import AppError

    settings = Settings(env="test", jwt_secret="j" * 64, cron_secret="c" * 64, anthropic_api_key="")
    with pytest.raises(AppError) as info:
        await get_llm(settings)
    assert info.value.code == "llm_unavailable"
    assert create_app(settings) is not None
