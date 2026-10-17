"""Build the real LLM provider from settings (shared by the pipeline and the API)."""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.llm import AnthropicProvider, LLMProvider
from app.ai.usage import DBUsageRecorder
from app.core.config import Settings

log = structlog.get_logger(__name__)


def build_llm(
    settings: Settings, sessionmaker: async_sessionmaker[AsyncSession]
) -> LLMProvider | None:
    """None when no API key is set: callers then use their no-LLM fallbacks."""
    key = settings.anthropic_api_key.get_secret_value()
    if not key:
        log.warning("anthropic_key_missing", effect="no-LLM fallbacks only")
        return None
    from anthropic import AsyncAnthropic

    return AnthropicProvider(AsyncAnthropic(api_key=key), DBUsageRecorder(sessionmaker))
