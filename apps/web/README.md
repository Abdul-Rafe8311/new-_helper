# NewsHelper web

Next.js (App Router, Cache Components), Tailwind v4, shadcn/ui. The browser calls `/api/*`, which `next.config.ts` rewrites to `API_URL` (default `http://localhost:8000`), so the `dp_session` cookie stays first-party.

| Command | What it does |
| --- | --- |
| `pnpm dev` | Dev server on :3000 |
| `pnpm build` / `pnpm start` | Production build / serve it |
| `pnpm lint` / `pnpm typecheck` | ESLint / route types + `tsc` |
| `pnpm test` | Vitest + Testing Library |
| `pnpm build:e2e` | Production build whose `/api/*` rewrite points at the e2e mock API (:3199) |
| `pnpm test:e2e` | Playwright tests against that build, using `e2e/mock-api.mjs` as the API (run `pnpm build:e2e` first) |
| `pnpm gen:api` | Regenerate `src/lib/api-schema.ts` from the API's OpenAPI schema (needs uv) |

Layout:

- `src/app/(auth)`: `/login`, `/signup`
- `src/app/(app)`: signed-in pages; the layout reads the session behind `<Suspense>` and sends new readers to `/onboarding`
- `src/proxy.ts`: optimistic cookie check that redirects to `/login?next=…`
- `src/components/paper`: the newspaper design system. See it all at `/styleguide`.
