"""Postgres-backed cache of decoded Google News links (table decoded_links)."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import DecodedLink


class DbLinkCache:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker

    async def get_many(self, urls: Sequence[str]) -> dict[str, str]:
        if not urls:
            return {}
        async with self._sessionmaker() as session:
            rows = await session.execute(
                select(DecodedLink.google_url, DecodedLink.publisher_url).where(
                    DecodedLink.google_url.in_(urls)
                )
            )
            return {str(google): str(publisher) for google, publisher in rows.tuples()}

    async def put_many(self, mapping: dict[str, str]) -> None:
        if not mapping:
            return
        async with self._sessionmaker() as session:
            stmt = insert(DecodedLink).values(
                [{"google_url": g, "publisher_url": p} for g, p in mapping.items()]
            )
            await session.execute(stmt.on_conflict_do_nothing(index_elements=["google_url"]))
            await session.commit()
