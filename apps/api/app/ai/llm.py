"""LLM access behind a protocol, with usage and cost accounting.

AnthropicProvider gets schema-valid JSON by offering one tool whose input schema is the
Pydantic model's JSON schema. Newer models reject a forced tool_choice, so the tool is
offered with tool_choice "auto" and the system prompt names it; the output is validated
and, if it fails, re-asked once with the validation error appended.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

import structlog
from pydantic import BaseModel, ValidationError

log = structlog.get_logger(__name__)

TOOL_NAME = "submit_result"
TOOL_INSTRUCTION = f"Respond only by calling the {TOOL_NAME} tool exactly once."
MAX_OUTPUT_TOKENS = 4096


@dataclass(frozen=True, slots=True)
class Price:
    """USD per million tokens."""

    input: float
    output: float
    cache_read: float
    cache_write: float


PRICES: dict[str, Price] = {
    "claude-haiku-5-5": Price(0.10, 0.50, 0.01, 0.125),
    "claude-sonnet-5-5": Price(2.00, 10.00, 0.20, 2.50),
}
DEFAULT_PRICE = PRICES["claude-sonnet-5-5"]  # unknown models are costed pessimistically


@dataclass(frozen=True, slots=True)
class LLMCall:
    model: str
    purpose: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    @property
    def cost_usd(self) -> float:
        p = PRICES.get(self.model, DEFAULT_PRICE)
        return (
            self.input_tokens * p.input
            + self.output_tokens * p.output
            + self.cache_read_tokens * p.cache_read
            + self.cache_write_tokens * p.cache_write
        ) / 1_000_000


class UsageRecorder(Protocol):
    async def record(self, call: LLMCall) -> None:
        """Persist one call's token usage and cost."""


class LLMProvider(Protocol):
    async def complete_json[T: BaseModel](
        self, system: str, prompt: str, schema: type[T], model: str, *, purpose: str = "generic"
    ) -> T:
        """Return the model's answer validated as `schema`."""


class LLMError(Exception):
    pass


class AnthropicProvider:
    def __init__(self, client: Any, recorder: UsageRecorder | None = None) -> None:
        self._client = client
        self._recorder = recorder

    async def _create(
        self, system: str, messages: list[dict[str, Any]], schema: type[BaseModel], model: str
    ) -> Any:
        return await self._client.messages.create(
            model=model,
            max_tokens=MAX_OUTPUT_TOKENS,
            # static system prompt first, marked cacheable
            system=[
                {
                    "type": "text",
                    "text": f"{system}\n\n{TOOL_INSTRUCTION}",
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[
                {
                    "name": TOOL_NAME,
                    "description": "Submit the final structured result.",
                    "input_schema": schema.model_json_schema(),
                }
            ],
            tool_choice={"type": "auto"},
            messages=messages,
        )

    async def _record(self, response: Any, model: str, purpose: str) -> None:
        if self._recorder is None:
            return
        u = response.usage
        await self._recorder.record(
            LLMCall(
                model=model,
                purpose=purpose,
                input_tokens=u.input_tokens or 0,
                output_tokens=u.output_tokens or 0,
                cache_read_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
                cache_write_tokens=getattr(u, "cache_creation_input_tokens", 0) or 0,
            )
        )

    async def complete_json[T: BaseModel](
        self, system: str, prompt: str, schema: type[T], model: str, *, purpose: str = "generic"
    ) -> T:
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        error: ValidationError | None = None
        for attempt in range(2):
            response = await self._create(system, messages, schema, model)
            await self._record(response, model, purpose)
            block = next((b for b in response.content if b.type == "tool_use"), None)
            if block is None:
                raise LLMError(f"model returned no {TOOL_NAME} call (stop: {response.stop_reason})")
            try:
                return schema.model_validate(block.input)
            except ValidationError as exc:
                error = exc
                log.warning("llm_validation_failed", attempt=attempt, purpose=purpose)
                messages = [
                    *messages,
                    {"role": "assistant", "content": [block.model_dump()]},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "is_error": True,
                                "content": f"Output failed validation, fix it and call "
                                f"{TOOL_NAME} again:\n{exc}",
                            }
                        ],
                    },
                ]
        raise LLMError(f"output still invalid after one retry: {error}")


class FakeLLM:
    """Scripted provider for tests: replies come from a callable or a queue of dicts.

    A reply is validated against the requested schema, like the real provider does.
    """

    def __init__(
        self,
        replies: list[dict[str, Any]] | None = None,
        responder: Callable[[str, type[BaseModel]], dict[str, Any]] | None = None,
        cost_per_call: float = 0.0,
        recorder: UsageRecorder | None = None,
    ) -> None:
        self._replies = list(replies or [])
        self._responder = responder
        self._cost = cost_per_call
        self._recorder = recorder
        self.calls: list[dict[str, str]] = []

    async def complete_json[T: BaseModel](
        self, system: str, prompt: str, schema: type[T], model: str, *, purpose: str = "generic"
    ) -> T:
        self.calls.append({"system": system, "prompt": prompt, "model": model, "purpose": purpose})
        if self._responder is not None:
            raw = self._responder(prompt, schema)
        elif self._replies:
            raw = self._replies.pop(0)
        else:
            raise LLMError("FakeLLM has no scripted reply left")
        if self._recorder is not None and self._cost:
            # price the call at exactly cost_per_call via output tokens of a known model
            tokens = round(self._cost / PRICES["claude-haiku-5-5"].output * 1_000_000)
            await self._recorder.record(
                LLMCall(model="claude-haiku-5-5", purpose=purpose, output_tokens=tokens)
            )
        return schema.model_validate(json.loads(json.dumps(raw)))
