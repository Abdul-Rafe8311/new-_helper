# Tasks

- [x] T0 Bootstrap
- [x] T1 CI & dev tooling
- [ ] T2 Backend core
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
