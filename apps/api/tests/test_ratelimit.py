from app.core.ratelimit import SlidingWindowLimiter


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_allows_up_to_the_limit_then_says_how_long_to_wait() -> None:
    clock = Clock()
    limiter = SlidingWindowLimiter(limit=2, window_seconds=10, clock=clock)
    assert limiter.hit("a") is None
    clock.now = 4
    assert limiter.hit("a") is None
    assert limiter.hit("a") == 6  # the first hit leaves the window at t=10


def test_the_window_slides_and_keys_are_independent() -> None:
    clock = Clock()
    limiter = SlidingWindowLimiter(limit=1, window_seconds=10, clock=clock)
    assert limiter.hit("a") is None
    assert limiter.hit("b") is None
    assert limiter.hit("a") is not None
    clock.now = 10
    assert limiter.hit("a") is None


def test_prune_forgets_idle_keys() -> None:
    clock = Clock()
    limiter = SlidingWindowLimiter(limit=1, window_seconds=10, clock=clock)
    limiter.hit("old")
    clock.now = 20
    limiter.hit("new")
    limiter.prune()
    assert list(limiter._hits) == ["new"]
