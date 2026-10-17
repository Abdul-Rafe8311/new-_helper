"""Fakes shared by the edition service and API tests."""

import json
import re
from datetime import date
from types import TracebackType
from typing import Any, cast

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.llm import FakeLLM, LLMCall
from app.ai.usage import note_usage
from app.editions.weather import Weather, WeatherService


class _SharedSession:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __aenter__(self) -> AsyncSession:
        return self._session

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None  # the test owns the session and its rollback


class SharedSessionMaker:
    """Stands in for async_sessionmaker so background work joins the test's transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def __call__(self) -> _SharedSession:
        return _SharedSession(self._session)


def sessionmaker_for(session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    return cast(async_sessionmaker[AsyncSession], SharedSessionMaker(session))


class ScopeRecorder:
    """Reports calls to the active track_usage() scope, like DBUsageRecorder does."""

    async def record(self, call: LLMCall) -> None:
        note_usage(call)


def plan_responder(prompt: str, schema: type[BaseModel]) -> dict[str, Any]:
    """Answer the composer's prompt with a valid plan built from the stories it contains."""
    stories = json.loads(prompt.split("STORIES", 1)[1].split("\n", 1)[1])
    ids = [s["id"] for s in stories]
    non_explore = [s["id"] for s in stories if not s["explore"]]
    explore = [s["id"] for s in stories if s["explore"]]
    sections = [
        {"name": "Fake Section One", "item_ids": non_explore[: len(non_explore) // 2 + 1]},
        {
            "name": "Fake Section Two",
            "item_ids": non_explore[len(non_explore) // 2 + 1 :] + explore,
        },
    ]
    sections = [s for s in sections if s["item_ids"]]
    first = stories[0]
    quote = re.split(r"(?<=[.!?])\s+", first["summary"])[0]
    return {
        "title_line": "The Fake Morning",
        "tagline": "Composed by a fake editor",
        "editor_note": "Good morning. Here is your paper.",
        "lead_id": non_explore[0],
        "sections": sections,
        "items": [
            {"id": i, "headline": f"Rewritten {i}", "summary": f"Rewrite of {i}."} for i in ids
        ],
        "three_things": ["First", "Second", "Third"],
        "quote": {"text": quote, "article_id": first["id"]},
        "quiz": [
            {"question": f"Question {n}?", "options": ["x", "y", "z"], "answer_index": n % 3}
            for n in range(3)
        ],
    }


def fake_editor(cost: float = 0.01) -> FakeLLM:
    return FakeLLM(responder=plan_responder, cost_per_call=cost, recorder=ScopeRecorder())


class StubWeather(WeatherService):
    def __init__(self, weather: Weather | None) -> None:
        self._weather = weather
        self.asked: list[tuple[str | None, date]] = []

    async def for_city(self, session: AsyncSession, city: str | None, day: date) -> Weather | None:
        self.asked.append((city, day))
        return self._weather
