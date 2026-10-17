"""LLM spend persisted in llm_usage, and the daily budget guard."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.llm import LLMCall
from app.models.ai import LLMUsage


def start_of_utc_day(now: datetime | None = None) -> datetime:
    now = now or datetime.now(UTC)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


async def spend_today(session: AsyncSession, now: datetime | None = None) -> float:
    total = await session.scalar(
        select(func.coalesce(func.sum(LLMUsage.cost_usd), 0.0)).where(
            LLMUsage.created_at >= start_of_utc_day(now)
        )
    )
    return float(total or 0.0)


class DBUsageRecorder:
    """Writes each call in its own short transaction so spend survives a later failure."""

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker

    async def record(self, call: LLMCall) -> None:
        async with self._sessionmaker() as session:
            session.add(
                LLMUsage(
                    model=call.model,
                    purpose=call.purpose,
                    input_tokens=call.input_tokens,
                    output_tokens=call.output_tokens,
                    cache_read_tokens=call.cache_read_tokens,
                    cache_write_tokens=call.cache_write_tokens,
                    cost_usd=call.cost_usd,
                )
            )
            await session.commit()


class BudgetGuard:
    """True once today's spend reaches the daily limit; callers then skip the LLM."""

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession], limit_usd: float) -> None:
        self._sessionmaker = sessionmaker
        self.limit_usd = limit_usd

    async def spent(self) -> float:
        async with self._sessionmaker() as session:
            return await spend_today(session)

    async def exceeded(self) -> bool:
        return await self.spent() >= self.limit_usd
