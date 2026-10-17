# Tasks

- [x] T0 Bootstrap
- [x] T1 CI & dev tooling
- [x] T2 Backend core
- [ ] T3 Web shell & design system
- [ ] T4 CD & deploy
- [ ] T5 Ingestion
- [ ] T6 Enrichment
- [ ] T7 Onboarding
- [ ] T8 Ranking & composer
- [ ] T9 PDF
- [ ] T10 Web reader & archive
- [ ] T11 Learning loop
- [ ] T12 Explore features
- [ ] T13 Docs & submission

## Deferred / notes

- T1: the image is built and smoke-tested in CI but not pushed; pushing to GHCR/Render belongs to T4 (CD).
- T1: the PR-title check uses `pull_request_target`, so it runs from `main`'s copy of the workflow and first applies to PRs opened after T1 merges.
- T1: `astral-sh/setup-uv` has no floating major tag, so it is pinned to `v10.3.0` (Dependabot bumps it).
- T1: cleanups for later: vitest config uses `__dirname` (Vite suggests `import.meta.dirname`); the Starlette TestClient warns that `httpx` is deprecated in favour of `httpx2`.
- T2: `/editions` and `/events` are auth-guarded 501 stubs (T8-T11); `/internal` only has `GET /internal/ping` until the pipeline endpoint lands.
- T2: the demo account has an unknown random password; it is entered only via `POST /auth/demo`.
- T2: migrations and seed were applied to Supabase `public`; local DB tests ran in a throwaway `test_*` schema that the fixtures drop afterwards.
- T2: dropped from the source registry because they failed validation: Al Jazeera (connection reset), Yahoo Finance (404), VentureBeat AI (429).
- T2: no rate limiting on `/auth/login` yet.
