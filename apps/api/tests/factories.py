"""Model factories for DB tests."""

import itertools
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models import Article, ReaderProfile, Source, SourceKind, User

_seq = itertools.count(1)
DEFAULT_PASSWORD = "correct-horse-battery"


async def make_user(
    session: AsyncSession,
    *,
    email: str | None = None,
    password: str = DEFAULT_PASSWORD,
    profile: dict[str, Any] | None = None,
    **fields: Any,
) -> User:
    n = next(_seq)
    user = User(
        email=email or f"reader{n}@example.com",
        password_hash=hash_password(password),
        display_name=fields.pop("display_name", f"Reader {n}"),
        profile=ReaderProfile(**(profile or {})),
        **fields,
    )
    session.add(user)
    await session.flush()
    return user


async def make_source(session: AsyncSession, **fields: Any) -> Source:
    n = next(_seq)
    source = Source(
        name=fields.pop("name", f"Source {n}"),
        kind=fields.pop("kind", SourceKind.RSS),
        url=fields.pop("url", f"https://example.com/feed{n}.xml"),
        **fields,
    )
    session.add(source)
    await session.flush()
    return source


async def make_article(session: AsyncSession, **fields: Any) -> Article:
    n = next(_seq)
    article = Article(
        url=fields.pop("url", f"https://example.com/story-{n}"),
        title=fields.pop("title", f"Story {n}"),
        **fields,
    )
    session.add(article)
    await session.flush()
    return article
