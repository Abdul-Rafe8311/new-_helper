# NewsHelper web

Next.js (App Router, Cache Components), Tailwind v4, shadcn/ui. The browser calls `/api/*`, which `next.config.ts` rewrites to `API_URL` (default `http://localhost:8000`), so the `dp_session` cookie stays first-party.

| Command | What it does |
| --- | --- |
| `pnpm dev` | Dev server on :3000 |
| `pnpm build` / `pnpm start` | Production build / serve it |
| `pnpm lint` / `pnpm typecheck` | ESLint / route types + `tsc` |
| `pnpm test` | Vitest + Testing Library |
| `pnpm test:e2e` | Playwright smoke tests against the production build (run `pnpm build` first) |
| `pnpm gen:api` | Regenerate `src/lib/api-schema.ts` from the API's OpenAPI schema (needs uv) |

Layout:

- `src/app/(auth)`: `/login`, `/signup`
- `src/app/(app)`: signed-in pages; the layout reads the session behind `<Suspense>` and sends new readers to `/onboarding`
- `src/proxy.ts`: optimistic cookie check that redirects to `/login?next=…`
- `src/components/paper`: the newspaper design system. See it all at `/styleguide`.
