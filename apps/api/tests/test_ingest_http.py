import asyncio

import httpx
import pytest
import respx
from tenacity import wait_none

from app.ingest.http import PoliteClient, RetryableStatusError, RobotsDisallowedError

UA = "NewsHelperBot/0.1 (+https://example.test)"


def _client(**kwargs: int) -> PoliteClient:
    return PoliteClient(UA, wait=wait_none(), **kwargs)


@respx.mock
async def test_retries_5xx_then_succeeds() -> None:
    route = respx.get("https://a.test/x").mock(
        side_effect=[httpx.Response(503), httpx.Response(502), httpx.Response(200, text="ok")]
    )
    async with _client() as http:
        response = await http.get("https://a.test/x")
    assert response.text == "ok"
    assert route.call_count == 3


@respx.mock
async def test_gives_up_after_three_attempts() -> None:
    route = respx.get("https://a.test/x").mock(return_value=httpx.Response(500))
    async with _client() as http:
        with pytest.raises(RetryableStatusError):
            await http.get("https://a.test/x")
    assert route.call_count == 3


@respx.mock
async def test_retries_timeouts() -> None:
    route = respx.get("https://a.test/x").mock(
        side_effect=[httpx.ConnectTimeout("slow"), httpx.Response(200, text="ok")]
    )
    async with _client() as http:
        assert (await http.get("https://a.test/x")).status_code == 200
    assert route.call_count == 2


@respx.mock
async def test_client_errors_are_returned_not_retried() -> None:
    route = respx.get("https://a.test/x").mock(return_value=httpx.Response(404))
    async with _client() as http:
        assert (await http.get("https://a.test/x")).status_code == 404
    assert route.call_count == 1


@respx.mock
async def test_sends_our_user_agent() -> None:
    route = respx.get("https://a.test/x").mock(return_value=httpx.Response(200))
    async with _client() as http:
        await http.get("https://a.test/x")
    assert route.calls.last.request.headers["user-agent"] == UA


@respx.mock
async def test_robots_disallow_blocks_and_is_cached() -> None:
    robots = respx.get("https://a.test/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nDisallow: /private\n")
    )
    page = respx.get("https://a.test/public").mock(return_value=httpx.Response(200))
    async with _client() as http:
        await http.get("https://a.test/public", respect_robots=True)
        with pytest.raises(RobotsDisallowedError):
            await http.get("https://a.test/private/x", respect_robots=True)
        assert not await http.robots_allows("https://a.test/private")
    assert robots.call_count == 1
    assert page.call_count == 1


@respx.mock
async def test_robots_named_agent_rules_apply() -> None:
    respx.get("https://a.test/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: NewsHelperBot\nDisallow: /\n")
    )
    async with _client() as http:
        assert not await http.robots_allows("https://a.test/anything")


@respx.mock
async def test_missing_robots_allows_everything() -> None:
    respx.get("https://a.test/robots.txt").mock(return_value=httpx.Response(404))
    async with _client() as http:
        assert await http.robots_allows("https://a.test/anything")


@respx.mock
async def test_robots_server_error_denies() -> None:
    respx.get("https://a.test/robots.txt").mock(return_value=httpx.Response(503))
    async with _client() as http:
        assert not await http.robots_allows("https://a.test/anything")


@respx.mock
async def test_robots_not_consulted_unless_asked() -> None:
    robots = respx.get("https://a.test/robots.txt").mock(return_value=httpx.Response(200))
    respx.get("https://a.test/feed").mock(return_value=httpx.Response(200))
    async with _client() as http:
        await http.get("https://a.test/feed")
    assert robots.call_count == 0


@respx.mock
async def test_per_domain_concurrency_is_capped() -> None:
    active = peak = 0

    async def slow(request: httpx.Request) -> httpx.Response:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        return httpx.Response(200)

    respx.get(url__regex=r"https://a\.test/.*").mock(side_effect=slow)
    async with _client(per_domain_limit=2) as http:
        await asyncio.gather(*(http.get(f"https://a.test/{i}") for i in range(8)))
    assert peak == 2


@respx.mock
async def test_global_concurrency_is_capped() -> None:
    active = peak = 0

    async def slow(request: httpx.Request) -> httpx.Response:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        return httpx.Response(200)

    respx.get(url__regex=r"https://.*\.test/.*").mock(side_effect=slow)
    async with _client(global_limit=3, per_domain_limit=2) as http:
        await asyncio.gather(*(http.get(f"https://d{i}.test/x") for i in range(12)))
    assert peak == 3
