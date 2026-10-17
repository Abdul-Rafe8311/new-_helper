# NewsHelper — project guide for Claude Code

## Product
NewsHelper is a personal morning newspaper (Eynvision hackathon). It learns what a reader cares about, gathers articles from across the web daily, and composes one personal paper: read on the web (click through, skip), download as a newspaper-style PDF, browse past editions. It improves with use.
Required: (1) great onboarding that captures interests, (2) daily PDF in traditional newspaper style, personalised in content AND presentation, (3) web reader + PDF download + archive, (4) learning from behaviour, (5) creative extras.
Evaluators review commit history and CI/CD: engineering hygiene matters as much as features.

Repo: https://github.com/Abdul-Rafe8311/new-_helper (product name NewsHelper; bot UA `NewsHelperBot/0.1 (+repo url)`).

## Stack (do not change without asking)
- `apps/web`: Next.js App Router, TypeScript strict, Tailwind, shadcn/ui, pnpm, vitest + Testing Library. Deployed on Vercel. Next.js rewrites `/api/*` to the API so auth cookies stay first-party.
- `apps/api`: Python 3.12, FastAPI, SQLAlchemy 2 async + asyncpg, Alembic, Pydantic v2, uv. Docker image on Render.
- DB: Postgres + pgvector on Supabase, for local dev too (no Docker locally). `DATABASE_URL` in `.env` uses `postgresql+asyncpg://` and the Supabase pooler, so asyncpg always gets `statement_cache_size=0`. CI uses a `pgvector/pgvector:pg16` service container. Files behind a `Storage` interface (local disk dev, Supabase Storage prod).
- Scraping: open source first — feedparser, Google News RSS search (googlenewsdecoder), HN Algolia, arXiv, trafilatura (newspaper4k fallback). Apify only as fallback when `APIFY_TOKEN` is set.
- AI: Anthropic SDK behind `LLMProvider`. `LLM_FAST_MODEL=claude-haiku-5-5`, `LLM_SMART_MODEL=claude-sonnet-5-5`. Embeddings behind `Embedder`, fastembed `BAAI/bge-small-en-v1.5` (384 dims).
- PDF: Jinja2 + WeasyPrint.
- Jobs: daily pipeline `ingest -> enrich -> learn -> compose -> render` is a Python CLI (`python -m app.pipeline --stage ...`), run by scheduled GitHub Actions in prod and on demand via an internal endpoint.
- **Memory rule:** the API runs in 512 MB. The API process never loads the embedding model; it uses vectors stored in Postgres. Fresh embeddings happen only in the pipeline.
- Cost rule: per-article work (embeddings, topics, summaries) is done once and shared by all readers; one smart-model call per reader per day.

## Repo map
```
apps/api/            FastAPI backend + pipeline
  app/main.py        app factory, /health
  app/core/          config (pydantic-settings), taxonomy, logging
  app/api/routers/   thin HTTP routers (added in T2)
  app/db/ models/    SQLAlchemy session, models, Alembic (T2)
  app/ingest/ ai/ personalize/ editions/ pdf/   pipeline domains (T5+)
  tests/             pytest
apps/web/            Next.js app (src/app, src/components, src/lib)
docs/decisions/      ADRs
.github/             CI/CD workflows (T1+)
TASKS.md             task checklist and deferred notes
```

## Commands
| Do | Command |
| --- | --- |
| Install all | `make install` |
| Run API / web / both | `make api` / `make web` / `make dev` |
| Test all | `make test` |
| Lint + typecheck all | `make lint` |
| Format | `make format` |
| API only | `cd apps/api && uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest` |
| Web only | `cd apps/web && pnpm lint && pnpm typecheck && pnpm test && pnpm build` |

Copy `.env.example` to `.env` at the repo root for local settings. Never print or commit `.env` or `DATABASE_URL`.

## Coding standards
- TypeScript strict, no `any`. Python fully typed; ruff + mypy (strict) clean.
- Business logic lives in services; routers stay thin.
- No real network calls in tests: fixtures, respx, fakes (FakeLLM, FakeEmbedder).
- Secrets only from env, never hard-coded or committed.
- Small, focused modules. Interfaces (protocols) at external boundaries: LLM, embedder, storage, fetchers.

## GIT WORKFLOW (mandatory for every task)
a. Start from fresh main: `git checkout main && git pull && git checkout -b feat/tNN-short-name`
b. Commit after every working sub-step with Conventional Commits (`feat:`, `fix:`, `test:`, `ci:`, `chore:`, `docs:`, `refactor:`). Aim for 5–12 focused commits per task, never one giant commit. Never commit secrets.
c. Before each commit, run lint + tests for the app you touched.
d. When the task is done: push, `gh pr create` with a body (What / Why / How tested / Checklist), watch CI with `gh pr checks --watch`, fix until green, then `gh pr merge --merge --delete-branch`. Use a merge commit, NOT squash, so every commit stays in main's history.
e. Tick the task in TASKS.md in the branch's last commit and note anything deferred.

## Done means
Lint clean, typecheck clean, tests pass, CI green on GitHub, PR merged.

## Reply style
When a task ends, reply in 5 lines or fewer.
