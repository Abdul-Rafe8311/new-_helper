# Deployment

Merging to `main` ships both apps. Vercel's own Git deploys are disabled (ignored build step `exit 0`), so GitHub Actions is the only path to production.

```
push to main -> CI (green) -> Deploy workflow
  image    build apps/api, push ghcr.io/<owner>/newshelper-api:<sha> and :latest
  api      alembic upgrade head -> Render deploy hook (imgURL=<sha image>) -> poll /health for the new git_sha (10 min)
  web      vercel pull -> vercel build --prod -> vercel deploy --prebuilt --prod
  smoke    web /, API /health at the deployed sha, POST /api/auth/demo + GET /api/auth/me through the web domain
```

Deploys run in the GitHub Environment `production`, so they appear in the repo's Deployments tab. Pull requests that touch `apps/web` get a Vercel preview, with the URL commented on the PR (`preview.yml`).

## GitHub Actions secrets

| Secret | Used by | Notes |
| --- | --- | --- |
| `DATABASE_URL` | deploy (migrations), daily pipeline | Supabase pooler, `postgresql+asyncpg://` |
| `JWT_SECRET` | Render env (same value) | `openssl rand -hex 32` |
| `CRON_SECRET` | Render env (same value) | `openssl rand -hex 32` |
| `RENDER_DEPLOY_HOOK_URL` | deploy | Render service -> Settings -> Deploy Hook. Contains a key; never log it |
| `VERCEL_TOKEN` | deploy, preview | Vercel account token |
| `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` | deploy, preview | From the project's Vercel settings |

## GitHub Actions variables (not secret)

| Variable | Value |
| --- | --- |
| `API_URL` | `https://newshelper-api.onrender.com` |
| `WEB_URL` | `https://new-helper-nine.vercel.app` |

## Render (service `newshelper-api`, see `render.yaml`)

Image-backed web service, health check `/health`, auto-deploy off. Env vars: `ENV=prod`, `LOG_LEVEL`, `WEB_URL`, `DEMO_EMAIL`, `STORAGE_BACKEND`, `SUPABASE_BUCKET`, and the secrets `DATABASE_URL`, `JWT_SECRET`, `CRON_SECRET`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`. The GHCR package `newshelper-api` must be public (or Render needs registry credentials).

## Vercel (project `new-helper`, root directory `apps/web`)

`API_URL` (the Render URL) for Production and Preview; `next.config.ts` reads it at build time for the `/api/*` rewrite. Vercel never gives "Sensitive" env vars to the CLI, so the deploy and preview workflows overwrite `API_URL` in the pulled env with the `API_URL` repo variable.

## Deploy manually

Actions -> **Deploy** -> *Run workflow* on `main` (redeploys the chosen commit). To run only the database step locally: `make migrate` with `DATABASE_URL` in `.env`.

## Roll back

Redeploy a previous image: in Render, *Manual Deploy -> Deploy an existing image* with `ghcr.io/<owner>/newshelper-api:<previous-sha>`, or POST the deploy hook with `&imgURL=<that image>`. Migrations are not reverted automatically; keep them backward compatible. Roll the web app back by promoting an earlier deployment in the Vercel dashboard.

## Daily pipeline

`daily-pipeline.yml` runs `python -m app.pipeline --stage <stage>` against the production database at 00:30 UTC (05:30 Pakistan time) and on demand (inputs `stage`, optional `user_email`). Implemented stages: `healthcheck` and `seed`; `all` runs the healthcheck and then whichever daily stages exist. Later tasks add ingest, enrich, learn, compose and render.
