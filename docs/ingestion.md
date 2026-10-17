# Ingestion

`python -m app.pipeline --stage ingest` gathers the day's articles once for every reader. It runs
in the daily GitHub Actions workflow (05:30 PKT) and on demand. No LLM is involved; per-article
work (extraction, hashing) is shared by all readers.

```
active sources + reader interests
   -> fetchers, concurrently (RSS, Google News search, HN, arXiv, Reddit, Apify)
   -> candidates: canonical URL, <= 48 h old, <= 40 newest per fetcher, URL deduped
   -> full text: feed body | arXiv abstract | trafilatura -> newspaper4k -> Apify (high_value only)
   -> drop: < 120 words, language not in ALLOWED_LANGUAGES, robots.txt disallowed
   -> dedupe by content hash -> upsert Articles -> PipelineRun row with stats
```

## Fetchers (`app/ingest/fetchers/`)

| Fetcher | Source | Notes |
| --- | --- | --- |
| `rss.py` | the registry's RSS feeds | conditional GET with the stored `etag` / `last_modified`; uses `content:encoded` as the body when it holds the whole article (>= 200 words) |
| `google_news.py` | `news.google.com/rss/search?q=<term>+when:1d` | one search per reader keyword/entity, US edition plus Pakistan (`en-PK`) for readers in Pakistan. Only `/rss/search`. No article body, so each link is decoded to the publisher URL with `googlenewsdecoder`, cached in `decoded_links`; failures are skipped. If more than 30% fail and `APIFY_TOKEN` is set, the rest go to `APIFY_GNEWS_ACTOR` |
| `hackernews.py` | HN Algolia | front page + stories of the last 24 h with 40+ points; Ask HN posts skipped |
| `arxiv.py` | arXiv API | newest per category, one request per 3 s; the abstract is the content |
| `reddit.py` | public JSON, top of the day | off unless `REDDIT_ENABLED`; subreddits in `REDDIT_SUBREDDITS`; 403/429 mean "nothing today" |
| `apify.py` | any Apify actor | only when `APIFY_TOKEN` is set: link decoding, high-value page extraction, or a generic actor-to-articles adapter. Runs are capped at $0.50 |

## Politeness and resilience (`app/ingest/http.py`)

- One `PoliteClient` for the whole run: 10 concurrent requests overall, 2 per domain, 10 s timeout.
- User agent `NewsHelperBot/0.1 (+<repo url>)`.
- `robots.txt` is fetched once per origin and cached for the run. Article pages are checked; feeds and public APIs are not. 4xx means no restrictions, 5xx or unreachable means deny.
- Retries (3 attempts, exponential backoff) on timeouts, connection errors, 5xx and 429.
- `Source.failure_count` goes up when a source fails and resets on success; five failures in a row set `active = false`. A source with several jobs (Google News queries) only fails when all of them fail.

## Stats

Every run writes a `pipeline_runs` row (`stage = 'ingest'`): `fetched`, `new`, `duplicates`, `dropped`, `failed`, `drop_reasons`, `sources_failed`, `sources_deactivated`, and `timings` (seconds per fetcher plus `_extract_seconds`).

## Reference run

Clean database, local machine, no Apify: 2,876 items fetched, 823 new articles stored, 247 duplicates, 103 dropped, 3 extraction failures, in 141 s (extraction 43 s).
