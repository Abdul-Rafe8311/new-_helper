# NewsHelper

[![CI](https://github.com/Abdul-Rafe8311/new-_helper/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Abdul-Rafe8311/new-_helper/actions/workflows/ci.yml) [![CodeQL](https://github.com/Abdul-Rafe8311/new-_helper/actions/workflows/codeql.yml/badge.svg?branch=main)](https://github.com/Abdul-Rafe8311/new-_helper/actions/workflows/codeql.yml)

**Your morning, on one page.** NewsHelper learns what you care about, gathers articles from across the web every day, and composes one personal morning newspaper. Read it on the web, click through to the originals, skip what you don't want, download the same edition as a newspaper-style PDF, and browse past editions. The more you read, the better your paper gets.

Built for the Eynvision hackathon.

## Quickstart

> Placeholder: full setup lands with the docs task.

```bash
git clone https://github.com/Abdul-Rafe8311/new-_helper.git && cd new-_helper
cp .env.example .env   # set DATABASE_URL to your Supabase session pooler URL
make install
make dev        # API on :8000, web on :3000
```

## Repository layout

| Path | What lives there |
| --- | --- |
| `apps/api` | FastAPI backend and daily pipeline (Python 3.12, uv) |
| `apps/web` | Next.js web app (TypeScript, Tailwind, pnpm) |
| `docs` | Architecture decisions and docs |

## Development

### Prerequisites

- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- Node.js LTS and pnpm (version pinned in `apps/web/package.json`)
- A Supabase project (Postgres + pgvector); there is no local Docker database
- Copy `.env.example` to `.env` and set `DATABASE_URL` to the Supabase session pooler URL

### Make targets

| Target | What it does |
| --- | --- |
| `make install` | Install API (uv) and web (pnpm) dependencies |
| `make dev` | API on :8000 and web on :3000 together |
| `make api` / `make web` | Run one app |
| `make test` | pytest + vitest |
| `make lint` | ruff, ruff format check, mypy, eslint, tsc |
| `make format` | Auto-fix lint and formatting |

### Pre-commit hooks

Hooks run ruff (lint + format), whitespace/YAML checks and gitleaks before every commit. Install them once after cloning:

```bash
uvx pre-commit install            # needs uv; or: pipx run pre-commit install
uvx pre-commit run --all-files    # optional: check the whole repo now
```

### CI

Every PR runs `CI` (path-filtered API, Docker and web jobs, gated by a single `CI OK` check), `CodeQL` and a Conventional Commits check on the PR title. `main` is protected: changes land through a PR with `CI OK` green, merged with a merge commit.
