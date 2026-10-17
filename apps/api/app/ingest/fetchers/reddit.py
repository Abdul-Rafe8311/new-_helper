"""Reddit public JSON (top of the day) for configured subreddits. Off unless REDDIT_ENABLED."""

from typing import Any

import structlog

from app.ingest.fetchers.base import epoch_to_datetime
from app.ingest.http import PoliteClient, RetryableStatusError
from app.ingest.types import FetchResult, RawItem
from app.ingest.urls import domain_of

log = structlog.get_logger(__name__)

REDDIT_HOSTS = ("reddit.com", "redd.it", "redditmedia.com", "redditstatic.com")


class RedditFetcher:
    def __init__(self, http: PoliteClient, subreddit: str, limit: int = 50) -> None:
        self._http = http
        self._subreddit = subreddit
        self._limit = limit
        self.label = f"reddit:r/{subreddit}"

    async def fetch(self) -> FetchResult:
        try:
            response = await self._http.get(
                f"https://www.reddit.com/r/{self._subreddit}/top.json",
                params={"t": "day", "limit": str(self._limit), "raw_json": "1"},
            )
        except RetryableStatusError as exc:
            # Reddit rate-limits anonymous clients freely; "nothing today", not a source failure.
            log.warning("reddit_blocked", subreddit=self._subreddit, status=exc.status_code)
            return FetchResult()
        if response.status_code >= 400:
            log.warning("reddit_blocked", subreddit=self._subreddit, status=response.status_code)
            return FetchResult()
        children = response.json().get("data", {}).get("children", [])
        items: list[RawItem] = []
        skipped = 0
        for child in children:
            post: dict[str, Any] = child.get("data", {})
            url = post.get("url")
            if (
                post.get("is_self")
                or post.get("over_18")
                or not url
                or domain_of(url).endswith(REDDIT_HOSTS)
            ):
                skipped += 1
                continue
            items.append(
                RawItem(
                    url=url,
                    title=post.get("title", ""),
                    published_at=epoch_to_datetime(post.get("created_utc")),
                    author=post.get("author"),
                    origin=self.label,
                )
            )
        return FetchResult(items=[i for i in items if i.title], skipped=skipped)
