# NewsHelper

**Your morning, on one page.** NewsHelper learns what you care about, gathers articles from across the web every day, and composes one personal morning newspaper. Read it on the web, click through to the originals, skip what you don't want, download the same edition as a newspaper-style PDF, and browse past editions. The more you read, the better your paper gets.

Built for the Eynvision hackathon.

## Quickstart

> Placeholder: full setup lands with the docs task.

```bash
git clone https://github.com/Abdul-Rafe8311/new-_helper.git && cd new-_helper
cp .env.example .env
make install
make db-up
make dev        # API on :8000, web on :3000
```

## Repository layout

| Path | What lives there |
| --- | --- |
| `apps/api` | FastAPI backend and daily pipeline (Python 3.12, uv) |
| `apps/web` | Next.js web app (TypeScript, Tailwind, pnpm) |
| `infra` | docker-compose for local Postgres + pgvector |
| `docs` | Architecture decisions and docs |
