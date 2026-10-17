import io

import httpx
import pytest
import respx
from PIL import Image

from app.pdf.images import MAX_EDGE, ImageCache, is_public_url, shrink
from app.pdf.qr import qr_data_uri


def png(width: int, height: int, mode: str = "RGB") -> bytes:
    buffer = io.BytesIO()
    Image.new(mode, (width, height), "navy").save(buffer, format="PNG")
    return buffer.getvalue()


def test_shrink_limits_the_long_edge_and_returns_jpeg():
    jpeg = shrink(png(3000, 2000))
    assert jpeg is not None
    with Image.open(io.BytesIO(jpeg)) as image:
        assert image.format == "JPEG"
        assert max(image.size) == MAX_EDGE


def test_shrink_flattens_transparency_and_rejects_junk_and_tiny_images():
    assert shrink(png(400, 300, "RGBA")) is not None
    assert shrink(b"not an image") is None
    assert shrink(png(40, 40)) is None  # a tracking pixel, not a picture


async def test_public_url_check_rejects_private_and_odd_schemes():
    assert not await is_public_url("http://127.0.0.1/a.jpg")
    assert not await is_public_url("http://10.0.0.5/a.jpg")
    assert not await is_public_url("file:///etc/passwd")
    assert not await is_public_url("not a url")


@pytest.fixture
def cache(tmp_path):
    return ImageCache(tmp_path / "images", "test-agent", check_public=False)


@respx.mock
async def test_fetch_resizes_and_caches(cache):
    route = respx.get("https://img.example.com/a.png").mock(
        return_value=httpx.Response(200, content=png(2400, 1600))
    )
    first = await cache.fetch("https://img.example.com/a.png")
    second = await cache.fetch("https://img.example.com/a.png")
    assert first is not None
    assert first.startswith("data:image/jpeg;base64,")
    assert second == first
    assert route.call_count == 1  # the second read came from disk


@respx.mock
async def test_fetch_follows_redirects_and_skips_broken_images(cache):
    respx.get("https://img.example.com/moved").mock(
        return_value=httpx.Response(302, headers={"location": "/final.png"})
    )
    respx.get("https://img.example.com/final.png").mock(
        return_value=httpx.Response(200, content=png(800, 600))
    )
    respx.get("https://img.example.com/gone.png").mock(return_value=httpx.Response(404))
    respx.get("https://img.example.com/html").mock(return_value=httpx.Response(200, text="<html>"))
    respx.get("https://img.example.com/boom").mock(side_effect=httpx.ConnectError("down"))
    assert await cache.fetch("https://img.example.com/moved") is not None
    assert await cache.fetch("https://img.example.com/gone.png") is None
    assert await cache.fetch("https://img.example.com/html") is None
    assert await cache.fetch("https://img.example.com/boom") is None


@respx.mock
async def test_fetch_many_returns_only_the_images_that_worked(cache):
    respx.get("https://img.example.com/ok.png").mock(
        return_value=httpx.Response(200, content=png(800, 600))
    )
    respx.get("https://img.example.com/bad.png").mock(return_value=httpx.Response(500))
    found = await cache.fetch_many(
        {"lead": "https://img.example.com/ok.png", "f1": "https://img.example.com/bad.png"}
    )
    assert set(found) == {"lead"}


@respx.mock
async def test_private_hosts_are_never_requested(tmp_path):
    guarded = ImageCache(tmp_path, "test-agent")  # check_public on
    route = respx.get("http://127.0.0.1/a.png").mock(return_value=httpx.Response(200))
    assert await guarded.fetch("http://127.0.0.1/a.png") is None
    assert not route.called


def test_qr_data_uri_is_a_png():
    uri = qr_data_uri("https://example.com/story")
    assert uri.startswith("data:image/png;base64,")
    assert len(uri) > 200
