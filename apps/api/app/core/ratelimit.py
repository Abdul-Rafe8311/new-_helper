"""A small in-process sliding-window rate limiter.

The API runs as one process on Render, so a dict is enough; if it ever scales out, swap the
store behind ``hit`` for Redis without touching callers.
"""

import time
from collections import deque
from collections.abc import Callable

_PRUNE_ABOVE = 1024


class SlidingWindowLimiter:
    def __init__(
        self, limit: int, window_seconds: float, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.limit = limit
        self.window = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}

    def hit(self, key: str) -> float | None:
        """Count a request. Returns None if allowed, else the seconds until it would be."""
        if len(self._hits) > _PRUNE_ABOVE:
            self.prune()
        now = self._clock()
        hits = self._hits.setdefault(key, deque())
        while hits and now - hits[0] >= self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return self.window - (now - hits[0])
        hits.append(now)
        return None

    def prune(self) -> None:
        """Forget keys with no recent hits so the dict cannot grow without bound."""
        now = self._clock()
        for key in [k for k, h in self._hits.items() if not h or now - h[-1] >= self.window]:
            del self._hits[key]
