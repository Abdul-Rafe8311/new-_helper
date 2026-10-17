import pytest

from app.core.config import Settings
from app.pipeline import (
    DatabaseStatus,
    PipelineError,
    StageContext,
    StageFn,
    StageNotImplementedError,
    alembic_head,
    main,
    parse_args,
    run_stage,
    verify_database,
)

CTX = StageContext(settings=Settings(env="test"))


def test_parse_args_defaults_and_empty_email() -> None:
    args = parse_args([])
    assert args.stage == "all"
    assert args.user_email is None
    assert parse_args(["--stage", "seed", "--user-email", ""]).user_email is None
    assert parse_args(["--user-email", "a@b.co"]).user_email == "a@b.co"


def test_parse_args_rejects_unknown_stage() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--stage", "bogus"])


def test_alembic_head_is_a_revision() -> None:
    assert alembic_head()


def test_verify_database() -> None:
    verify_database(DatabaseStatus(pgvector=True, revision="abc"), "abc")
    with pytest.raises(PipelineError, match="pgvector"):
        verify_database(DatabaseStatus(pgvector=False, revision="abc"), "abc")
    with pytest.raises(PipelineError, match="revision"):
        verify_database(DatabaseStatus(pgvector=True, revision=None), "abc")


async def test_run_stage_dispatches_to_the_named_stage() -> None:
    calls: list[str] = []

    async def seed(ctx: StageContext) -> None:
        calls.append("seed")

    await run_stage("seed", CTX, {"seed": seed})
    assert calls == ["seed"]


async def test_run_stage_unimplemented_stage_raises() -> None:
    with pytest.raises(StageNotImplementedError):
        await run_stage("ingest", CTX, {})


async def test_all_runs_healthcheck_then_implemented_daily_stages() -> None:
    calls: list[str] = []

    def recorder(name: str) -> StageFn:
        async def stage(ctx: StageContext) -> None:
            calls.append(name)

        return stage

    fns = {n: recorder(n) for n in ("healthcheck", "ingest", "render")}
    await run_stage("all", CTX, fns)
    assert calls == ["healthcheck", "ingest", "render"]


def test_main_exit_codes(monkeypatch: pytest.MonkeyPatch) -> None:
    async def boom(stage: str, ctx: StageContext) -> None:
        raise PipelineError("boom")

    monkeypatch.setattr("app.pipeline.run_stage", boom)
    assert main(["--stage", "healthcheck"]) == 1

    async def todo(stage: str, ctx: StageContext) -> None:
        raise StageNotImplementedError("todo")

    monkeypatch.setattr("app.pipeline.run_stage", todo)
    assert main(["--stage", "ingest"]) == 2
