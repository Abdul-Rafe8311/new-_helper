# NewsHelper

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

## Pre-commit hooks

Hooks run ruff (lint + format), whitespace/YAML checks and gitleaks before every commit. Install them once after cloning:

```bash
uvx pre-commit install            # needs uv; or: pipx run pre-commit install
uvx pre-commit run --all-files    # optional: check the whole repo now
```
