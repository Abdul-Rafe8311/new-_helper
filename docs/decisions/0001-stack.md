# ADR 0001: Technology stack

- Status: accepted
- Date: 2026-10-17

## Context

NewsHelper scrapes and enriches hundreds of articles a day, personalises an edition per reader, renders a newspaper-style PDF and serves a web reader. It is built in one day for a hackathon where evaluators review commit history and CI/CD, so the stack must be fast to build, cheap to run and easy to show in GitHub.

## Decision

| Layer | Choice | Why |
| --- | --- | --- |
| Web | Next.js (App Router, TypeScript strict), Tailwind, shadcn/ui on Vercel | Fast UI work, free preview deploy per PR |
| API | FastAPI, Python 3.12, SQLAlchemy 2 async, Alembic, Pydantic v2, uv | Python has the best scraping, NLP and PDF libraries |
| Data | Postgres + pgvector on Supabase (local dev too); pgvector service container in CI | One database for records and vectors, plus file storage |
| Scraping | feedparser, Google News RSS (googlenewsdecoder), HN Algolia, arXiv, trafilatura, newspaper4k | Open source first; Apify only as a token-gated fallback |
| AI | Claude Haiku 5.5 for bulk work, Sonnet 5.5 as editor, behind an `LLMProvider` interface; fastembed `bge-small-en-v1.5` (384 dims) behind an `Embedder` interface | Cheap model for volume, strong model for the single call that shapes each paper; local embeddings cost nothing |
| PDF | Jinja2 + WeasyPrint | Real print CSS: columns, running headers, page numbers |
| Jobs | Daily pipeline as a Python CLI run by scheduled GitHub Actions | No paid worker server; runs visible in the Actions tab |
| Deploy | API Docker image on Render, web on Vercel; Next.js rewrites `/api/*` to the API | Free tiers; first-party auth cookies |

## Consequences

- Per-article work (embeddings, topics, summaries) runs once in the pipeline and is shared by every reader, so each reader costs about one editor call per day.
- The API runs in 512 MB on Render, so it never loads the embedding model; it only uses vectors already stored in Postgres.
- Local dev has no Docker, so it uses Supabase through its pooler; asyncpg runs with `statement_cache_size=0` because poolers break prepared-statement caching.
- Two languages in one monorepo means two toolchains in CI, kept fast with path filters.
