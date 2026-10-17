"""Polite HTTP client shared by every fetcher and the extractor.

- one global concurrency cap and a per-domain cap
- robots.txt fetched once per origin and cached for the run (article pages only: feeds and
  public APIs are published for machines)
- tenacity retries with exponential backoff on timeouts, connection errors, 5xx and 429
"""

import asyncio
from collections import defaultdict
from types import TracebackType
from typing import Self
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx
import structlog
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tenacity.wait import wait_base

from app.ingest.urls import domain_of

log = structlog.get_logger(__name__)

GLOBAL_LIMIT = 10
PER_DOMAIN_LIMIT = 2
TIMEOUT_SECONDS = 10.0
MAX_ATTEMPTS = 3


class RetryableStatusError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"retryable HTTP status {status_code}")
        self.status_code = status_code


class RobotsDisallowedError(Exception):
    """The site's robots.txt forbids fetching this URL for our user agent."""


class PoliteClient:
    def __init__(
        self,
        user_agent: str,
        *,
        client: httpx.AsyncClient | None = None,
        global_limit: int = GLOBAL_LIMIT,
        per_domain_limit: int = PER_DOMAIN_LIMIT,
        wait: wait_base | None = None,
    ) -> None:
        self.user_agent = user_agent
        self._client = client or httpx.AsyncClient(
            timeout=TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": user_agent, "Accept-Language": "en"},
        )
        self._owns_client = client is None
        self._global = asyncio.Semaphore(global_limit)
        self._per_domain: defaultdict[str, asyncio.Semaphore] = defaultdict(
            lambda: asyncio.Semaphore(per_domain_limit)
        )
        # One in-flight/finished lookup per origin: a slow site never blocks other origins.
        self._robots: dict[str, asyncio.Task[RobotFileParser | None]] = {}
        self._wait = wait if wait is not None else wait_exponential(multiplier=0.5, max=8)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        respect_robots: bool = False,
    ) -> httpx.Response:
        """GET with limits and retries. 4xx (except 429) is returned for the caller to judge."""
        if respect_robots and not await self.robots_allows(url):
            raise RobotsDisallowedError(url)
        retrying = AsyncRetrying(
            stop=stop_after_attempt(MAX_ATTEMPTS),
            wait=self._wait,
            retry=retry_if_exception_type(
                (httpx.TimeoutException, httpx.TransportError, RetryableStatusError)
            ),
            reraise=True,
        )
        async for attempt in retrying:
            with attempt:
                return await self._once(url, headers, params)
        raise AssertionError("unreachable")  # pragma: no cover

    async def _once(
        self, url: str, headers: dict[str, str] | None, params: dict[str, str] | None
    ) -> httpx.Response:
        async with self._global, self._per_domain[domain_of(url)]:
            response = await self._client.get(url, headers=headers, params=params)
        if response.status_code >= 500 or response.status_code == 429:
            raise RetryableStatusError(response.status_code)
        return response

    async def robots_allows(self, url: str) -> bool:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            self._robots[origin] = asyncio.ensure_future(self._load_robots(origin))
        parser = await self._robots[origin]
        return True if parser is None else parser.can_fetch(self.user_agent, url)

    async def _load_robots(self, origin: str) -> RobotFileParser | None:
        """None means no restrictions. 4xx = no robots file (RFC 9309); 5xx/unreachable = deny."""
        try:
            response = await self._client.get(f"{origin}/robots.txt")
        except httpx.HTTPError:
            log.info("robots_unreachable", origin=origin)
            return _deny_all()
        if response.status_code >= 500:
            return _deny_all()
        if response.status_code >= 400:
            return None
        parser = RobotFileParser()
        parser.parse(response.text.splitlines())
        return parser


def _deny_all() -> RobotFileParser:
    parser = RobotFileParser()
    parser.parse(["User-agent: *", "Disallow: /"])
    return parser
