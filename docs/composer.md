# Ranking and the edition composer

Every reader gets one paper a day. Ranking is a transparent weighted score, so each story has an
honest "Why this?"; one smart-model call per reader then plays editor-in-chief. Code lives in
`apps/api/app/personalize` (ranking) and `apps/api/app/editions` (composer, weather, service).

## Pipeline for one reader

```
retrieve  ->  score  ->  select  ->  compose (1 LLM call)  ->  persist
```

1. **Retrieve** (`retrieve.py`): summarised cluster representatives from the last 24h, as the union of
   the pgvector top 300 by cosine to `interest_vector`, a Postgres full-text match on the reader's
   keywords and entities, and the biggest multi-outlet clusters. Blocked topics, keywords and
   sources, and anything printed in the last 7 editions (by article or story cluster), are excluded.
2. **Score** (`score.py`, weights in `config.py`):
   `score = (0.40 semantic + 0.20 topic + 0.15 match + 0.10 recency + 0.10 importance + 0.05 novelty) x source multiplier - penalties`.
   Each component is in [0, 1]; the weighted contributions are stored per item as `score_breakdown`.

   | Component | Definition |
   | --- | --- |
   | semantic | cosine(article, interest_vector), clipped to [0, 1] |
   | topic | best of article topic score x profile weight |
   | match | `1 - 0.5^hits` over profile keywords/entities named in the article |
   | recency | `0.5^(age / 12h)` |
   | importance | `min(1, log(1+n) / log(11)) x source quality`, n = outlets in the cluster |
   | novelty | `1 - ` strongest profile weight among the article's topics |

   The multiplier is `1 + 0.5 x source_affinity` (affinity in [-1, 1]). Penalties: already seen
   (-0.25), low-quality source (-0.10).
3. **Select** (`select.py`): item count from reading time (5 min -> 8, 10 -> 14, 20 -> 22,
   interpolated). With "surprise me" on, about 15% of slots are explore picks: high-quality stories
   whose leading topics are outside the reader's top five. The rest is chosen by MMR
   (lambda 0.7) with at most 2 items per source and 1 per cluster. "Why this?" comes from the
   strongest explainable component ("Because you follow ...", "Big story: 9 outlets covering it",
   "Outside your usual beats").
4. **Compose** (`compose.py`): the model sees the chosen stories under short ids (`a1`, `a2`, ...) and
   returns title line, tagline, an editor's note to the reader, a lead, reader-specific sections,
   rewritten headlines and summaries at the reader's depth, three takeaways, a quote and a
   three-question quiz. Every id is checked against the stories it was given:
   - invented ids, or an explore story as lead -> the **template layout** is used instead;
   - omitted or repeated stories, an unverifiable quote and malformed quiz questions are repaired or dropped;
   - the quote must appear word for word in its story's headline, summary or key facts.

   The template layout (also used with no API key or when the daily LLM budget is spent) groups by
   topic, never needs the LLM, and is deterministic.
5. **Persist** (`service.py`): `Edition` (layout JSON, stats) plus `EditionItem` rows with slot,
   rewritten copy, why text, score and breakdown.

## Edition service

- One edition per `(user, date)`. `generate_edition` returns the existing one unless `force` is set;
  `force` is limited to 3 regenerations per day (HTTP 429 after that).
- Status goes `pending -> ready | failed`. A `failed` edition is retried by the next run; a `pending`
  one older than 15 minutes is treated as abandoned.
- `prepare()` reserves the row (the unique constraint settles races) and `build()` does the work, so
  the API can answer 202 at once and finish in the background.
- Stats: items, sources, topics, top topics, explore items, LLM calls and cost (tracked per edition
  with a context variable, so concurrent builds do not mix), and whether the LLM or template composed it.

## Onboarding hook

`POST /onboarding/complete` opens today's edition and runs `ComposerEditionGenerator`
(`app/onboarding/generator.py`) in the background, which calls `EditionService.run`. While it
builds, `stats.stage` moves through `gathering` (retrieve), `choosing` (score and select),
`writing` (the LLM call) and `typesetting` (persist), then `done`; the finale animation polls
`GET /onboarding/status` for it. The same stages are written for regenerations and the daily stage.

## API

| Route | |
| --- | --- |
| `GET /editions/today` | today's edition in the reader's timezone (404 until one exists) |
| `GET /editions/{date}` | a specific day |
| `GET /editions` | archive: date, title, item count, top topics (ready editions) |
| `POST /editions/today/regenerate` | 202; starts a build, poll `GET /editions/today` |

## Pipeline stage

`python -m app.pipeline --stage compose [--user-email EMAIL]` builds one paper for every onboarded
reader, dated in that reader's timezone, five at a time. It is part of `--stage all` (after
`enrich`) in `daily-pipeline.yml`, and is idempotent: a second run costs nothing. It exits non-zero
only when no reader at all got a paper.

## Weather

Open-Meteo geocoding + forecast (no key), cached per city per day in `weather_cache`; a failure just
leaves the masthead without weather.

## Cost

One `LLM_SMART_MODEL` call per reader per day. Input is the profile plus 8-22 stories (a few
thousand tokens); the static system prompt is cache-marked.
