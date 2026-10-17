"""Daily pipeline CLI: ingest -> enrich -> learn -> compose -> render.

Run by the scheduled GitHub Actions workflow against the prod database:

    python -m app.pipeline --stage all|ingest|enrich|learn|compose|render|seed|healthcheck
                           [--user-email EMAIL]

Implemented so far: healthcheck, seed, ingest, enrich, learn, compose and render; later tasks
register the other daily stages in STAGE_FNS.
"""

import argparse
import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import structlog
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.db.session import get_engine, get_sessionmaker
from app.ingest.fetchers.apify import ApifyActorRunner
from app.ingest.http import PoliteClient
from app.ingest.service import IngestService
from app.scripts.seed import run_seed

log = structlog.get_logger(__name__)

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"

DAILY_STAGES = ("ingest", "enrich", "learn", "compose", "render")
STAGES = ("all", *DAILY_STAGES, "seed", "healthcheck")


@dataclass(frozen=True)
class StageContext:
    settings: Settings
    user_email: str | None = None


StageFn = Callable[[StageContext], Awaitable[None]]


class PipelineError(Exception):
    """A stage found the system in a state it cannot work with."""


class StageNotImplementedError(PipelineError):
    pass


@dataclass(frozen=True)
class DatabaseStatus:
    pgvector: bool
    revision: str | None


async def inspect_database(conn: AsyncConnection) -> DatabaseStatus:
    await conn.execute(text("SELECT 1"))
    pgvector = (
        await conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
    ).scalar() is not None
    has_version_table = (
        await conn.execute(text("SELECT to_regclass('alembic_version')"))
    ).scalar() is not None
    revision = None
    if has_version_table:
        revision = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar()
    return DatabaseStatus(pgvector=pgvector, revision=revision)


def verify_database(status: DatabaseStatus, head: str | None) -> None:
    if not status.pgvector:
        raise PipelineError("pgvector extension is not installed")
    if status.revision != head:
        raise PipelineError(f"database is at revision {status.revision}, expected head {head}")


def alembic_head() -> str | None:
    return ScriptDirectory.from_config(Config(str(ALEMBIC_INI))).get_current_head()


async def healthcheck(ctx: StageContext) -> None:
    """Fail unless the database is reachable, has pgvector and is migrated to head."""
    async with get_engine().connect() as conn:
        status = await inspect_database(conn)
    verify_database(status, alembic_head())
    log.info("healthcheck_ok", revision=status.revision, env=ctx.settings.env)


async def seed(ctx: StageContext) -> None:
    await run_seed(ctx.settings)


async def ingest(ctx: StageContext) -> None:
    """Fetch every active source and today's reader queries, extract and store new articles."""
    settings = ctx.settings
    runner = (
        ApifyActorRunner(settings.apify_token.get_secret_value())
        if settings.apify_enabled
        else None
    )
    async with PoliteClient(settings.user_agent) as http:
        service = IngestService.from_settings(settings, get_sessionmaker(), http, runner)
        stats = await service.run()
    summary = stats.as_dict()
    summary.pop("timings")
    log.info("ingest_done", **summary)


async def enrich(ctx: StageContext) -> None:
    from app.enrich.stage import enrich as run  # lazy: keeps AI imports off other stages

    await run(ctx.settings)


async def learn(ctx: StageContext) -> None:
    from app.personalize.stage import learn as run  # lazy: keeps the learner off other stages

    await run(ctx.settings, ctx.user_email)


async def compose(ctx: StageContext) -> None:
    from app.editions.stage import compose as run  # lazy: keeps AI imports off other stages

    await run(ctx.settings, ctx.user_email)


async def render(ctx: StageContext) -> None:
    from app.pdf.stage import RenderFailedError
    from app.pdf.stage import render as run  # lazy: keeps WeasyPrint off the other stages

    try:
        await run(ctx.settings, ctx.user_email)
    except RenderFailedError as exc:
        raise PipelineError(str(exc)) from exc


STAGE_FNS: dict[str, StageFn] = {
    "healthcheck": healthcheck,
    "seed": seed,
    "ingest": ingest,
    "enrich": enrich,
    "learn": learn,
    "compose": compose,
    "render": render,
}


async def run_stage(stage: str, ctx: StageContext, fns: dict[str, StageFn] = STAGE_FNS) -> None:
    if stage == "all":
        await fns["healthcheck"](ctx)
        for name in DAILY_STAGES:
            if name in fns:
                log.info("stage_start", stage=name)
                await fns[name](ctx)
            else:
                log.info("stage_skipped", stage=name, reason="not implemented yet")
        return
    if stage not in fns:
        raise StageNotImplementedError(f"stage {stage!r} is not implemented yet")
    log.info("stage_start", stage=stage, user_email=ctx.user_email)
    await fns[stage](ctx)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m app.pipeline", description=__doc__)
    parser.add_argument("--stage", choices=STAGES, default="all")
    parser.add_argument("--user-email", default=None, help="limit per-reader stages to one reader")
    args = parser.parse_args(argv)
    args.user_email = args.user_email or None  # the workflow passes "" when the input is empty
    return args


async def _main(args: argparse.Namespace) -> None:
    settings = get_settings()
    configure_logging(settings)
    try:
        await run_stage(args.stage, StageContext(settings=settings, user_email=args.user_email))
    finally:
        await get_engine().dispose()
    log.info("pipeline_done", stage=args.stage)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        asyncio.run(_main(args))
    except PipelineError as exc:
        log.error("pipeline_failed", stage=args.stage, error=str(exc))
        return 2 if isinstance(exc, StageNotImplementedError) else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
