from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

from app.ai.llm import TOOL_NAME, AnthropicProvider, FakeLLM, LLMCall, LLMError


class Out(BaseModel):
    headline: str
    n: int


def message(payload: dict[str, Any], tool_id: str = "tu_1") -> SimpleNamespace:
    block = SimpleNamespace(
        type="tool_use", id=tool_id, input=payload, model_dump=lambda: {"type": "tool_use"}
    )
    usage = SimpleNamespace(
        input_tokens=1000,
        output_tokens=200,
        cache_read_input_tokens=3000,
        cache_creation_input_tokens=0,
    )
    return SimpleNamespace(content=[block], usage=usage, stop_reason="tool_use")


class FakeClient:
    """Stands in for AsyncAnthropic: no network."""

    def __init__(self, *responses: SimpleNamespace) -> None:
        self.requests: list[dict[str, Any]] = []
        self._responses = list(responses)
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kwargs: Any) -> SimpleNamespace:
        self.requests.append(kwargs)
        return self._responses.pop(0)


class ListRecorder:
    def __init__(self) -> None:
        self.calls: list[LLMCall] = []

    async def record(self, call: LLMCall) -> None:
        self.calls.append(call)


async def test_valid_output_is_parsed_cached_and_costed() -> None:
    client, rec = FakeClient(message({"headline": "h", "n": 2})), ListRecorder()
    out = await AnthropicProvider(client, rec).complete_json(
        "sys", "prompt", Out, "claude-haiku-5-5", purpose="summaries"
    )
    assert out == Out(headline="h", n=2)
    req = client.requests[0]
    assert req["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert req["tools"][0]["name"] == TOOL_NAME
    assert req["tools"][0]["input_schema"] == Out.model_json_schema()
    assert req["tool_choice"] == {"type": "auto"}  # forced tool use is rejected by new models
    (call,) = rec.calls
    assert call.purpose == "summaries"
    # 1000 in @0.10 + 200 out @0.50 + 3000 cache reads @0.01 per MTok
    assert call.cost_usd == pytest.approx((100 + 100 + 30) / 1_000_000)


async def test_invalid_output_is_retried_once_with_the_error_appended() -> None:
    client = FakeClient(message({"headline": "h"}), message({"headline": "h", "n": 1}, "tu_2"))
    rec = ListRecorder()
    out = await AnthropicProvider(client, rec).complete_json("s", "p", Out, "claude-haiku-5-5")
    assert out.n == 1
    retry_messages = client.requests[1]["messages"]
    assert retry_messages[-1]["content"][0]["is_error"] is True
    assert "n" in retry_messages[-1]["content"][0]["content"]
    assert len(rec.calls) == 2  # both attempts are billed


async def test_still_invalid_after_retry_raises() -> None:
    client = FakeClient(message({}), message({}))
    with pytest.raises(LLMError, match="still invalid"):
        await AnthropicProvider(client).complete_json("s", "p", Out, "claude-haiku-5-5")
    assert len(client.requests) == 2


async def test_missing_tool_call_raises() -> None:
    empty = SimpleNamespace(
        content=[SimpleNamespace(type="text")],
        usage=SimpleNamespace(input_tokens=1, output_tokens=1),
        stop_reason="end_turn",
    )
    with pytest.raises(LLMError, match="no submit_result"):
        await AnthropicProvider(FakeClient(empty)).complete_json("s", "p", Out, "m")


def test_unknown_model_is_costed_like_sonnet() -> None:
    assert LLMCall(model="mystery", purpose="x", input_tokens=1_000_000).cost_usd == 2.0


async def test_fake_llm_validates_against_the_schema() -> None:
    llm = FakeLLM([{"headline": "a", "n": 1}, {"headline": "a"}])
    assert (await llm.complete_json("s", "p", Out, "m")).n == 1
    with pytest.raises(ValueError, match="n"):
        await llm.complete_json("s", "p", Out, "m")
    assert len(llm.calls) == 2
