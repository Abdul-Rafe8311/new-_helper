# NewsHelper design system

One product language from the homepage to the reader. It is derived from the dashboard (the reader), whose
values live in `apps/web/src/app/globals.css`; nothing here is invented. Before/after screenshots at matching
sizes and themes are in `docs/design/` (`m` = 390px, `d` = 1440px; light/dark in the file name).

## What the dashboard actually uses

| Thing | Value |
| --- | --- |
| Canvas / surface | `--canvas` `#fbfbfc` / `#0b0b0d`, `--surface` `#fff` / `#151518` |
| Paper / ink / muted / rule | `#f7f3ea` `#1a1714` `#625b51` `#d6ccbb`; dark `#1c1b19` `#e8e2d7` `#a69e91` `#3b3833` |
| Accent (primary action, kickers) | `#a4161a` light, `#e2645f` dark |
| Error | `--destructive` `#b42318` / `#f07167`, used only for errors |
| Brand blue | `--brand` `#2f5fd0` (the "For You" glow and the wordmark's full stop outside the reader) |
| Glow | one soft colour wash behind the top-left of every page (`ambient-layer`) |
| Fonts | Fraunces (display), Source Serif 4 (prose), Inter (interface) |

## Roles

- **Fraunces Black**: the wordmark `NewsHelper.`, a reader's own paper name, and article headlines.
- **Inter**: every page title (`page-title`: 800, -0.03em), control, label and card headline.
- **Source Serif 4**: ledes (`lede`: italic, muted), editor notes and long-form prose.
- **Kicker** (`kicker`): 0.72rem uppercase, 0.14em tracking, for step labels and section labels.

## Components

- `Brand` (`components/brand`): the only wordmark. Used by the landing nav, sign-in/up card, onboarding, the reader masthead and 404/error pages. Its full stop follows `--cat` (the reader's category colour; brand blue elsewhere through `.brand-scope`).
- `StaticAmbient`: the reader's glow, held still, for landing, auth, onboarding and error pages.
- `Button`: pill, 40px (`lg` 44px), sentence case, 14px/600. `accent` is the single primary action; `outline` secondary; `ghost` tertiary; `default` is ink. Press scale 0.98, disabled and focus ring (3px, `--ring`) are shared; all motion is off under `prefers-reduced-motion`.
- `Input`: 44px, 12px radius, surface fill. `FormField`: label, control, then hint or error (with icon); password fields have a show/hide toggle.
- `Chip` (topics): pill, ink fill when selected. `card` utility: 1px rule, 16px radius, shared shadow.
- `EmptyState`, `PixelScan` (decorative loader), `ThemeToggle` (one next-themes mechanism, stored in `localStorage`, on every route).
- Radii: pills for controls and chips, 12px fields, 16px cards, 24px panels.

## Pages

- **Landing** uses the same tokens (light and dark), the shared wordmark, one primary action ("Build my paper"), and previews built to match the real web edition (saturated category card), the PDF (broadsheet masthead) and the archive (edition cards). It is labelled "Sample edition".
- **Sign-in / sign-up**: canvas + glow, card with wordmark, theme toggle and close; Inter title, serif lede, one accent button with loading state; entered values are kept after any error.
- **Onboarding**: the reader's canvas and masthead; a five-segment progress bar; each step says in one sentence how it shapes the paper.
- **Reader, archive, saved, interests, settings**: unchanged structure; archive tags, section rules, menus, empty states and settings cards now use the shared tokens.
- **Print character**: the newspaper PDF and the masthead preview keep their serif broadsheet look on purpose.

## Test accounts (mock API only)

`e2e/mock-api.mjs` provides `reader@example.com` / `correct-horse` (finished reader), `taken@example.com` (cannot register) and any other email with an 8+ character password (new reader who must onboard). None is real.
