"""Shared FastAPI dependencies."""

import hmac
from typing import Annotated

from fastapi import Cookie, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.llm import LLMProvider
from app.ai.usage import BudgetGuard
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import SESSION_COOKIE, decode_session_token
from app.db.session import get_session, get_sessionmaker
from app.models import User
from app.onboarding.generator import EditionGenerator, StubEditionGenerator

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


async def current_user(
    session: SessionDep,
    settings: SettingsDep,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> User:
    user_id = decode_session_token(token, settings) if token else None
    if user_id is None:
        raise AppError(401, "not_authenticated", "Sign in to continue")
    result = await session.execute(
        select(User).options(selectinload(User.profile)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise AppError(401, "not_authenticated", "Sign in to continue")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


async def require_cron_secret(
    settings: SettingsDep,
    x_cron_secret: Annotated[str | None, Header()] = None,
) -> None:
    expected = settings.cron_secret.get_secret_value()
    if not x_cron_secret or not hmac.compare_digest(x_cron_secret.encode(), expected.encode()):
        raise AppError(403, "forbidden", "Invalid or missing X-Cron-Secret")


_llm_cache: dict[str, LLMProvider] = {}


async def get_llm(settings: SettingsDep) -> LLMProvider:
    """The real Anthropic provider; tests override this dependency with a FakeLLM."""
    from app.ai.factory import build_llm

    key = settings.anthropic_api_key.get_secret_value()
    sessionmaker = get_sessionmaker()
    if not key:
        raise AppError(503, "llm_unavailable", "AI features are not configured")
    if await BudgetGuard(sessionmaker, settings.llm_daily_budget_usd).exceeded():
        raise AppError(503, "llm_budget_exceeded", "AI features are resting until tomorrow")
    if key not in _llm_cache:
        provider = build_llm(settings, sessionmaker)
        assert provider is not None  # key is set
        _llm_cache[key] = provider
    return _llm_cache[key]


LLMDep = Annotated[LLMProvider, Depends(get_llm)]


def get_edition_generator() -> EditionGenerator:
    """Task 8 swaps the stub for the real ranker and composer."""
    return StubEditionGenerator(get_sessionmaker())


EditionGeneratorDep = Annotated[EditionGenerator, Depends(get_edition_generator)]
