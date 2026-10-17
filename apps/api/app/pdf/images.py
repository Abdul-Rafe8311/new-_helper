"""Story images for print: download, shrink to at most 1200px, cache on disk, skip failures.

A broken, slow, tiny or non-image URL never blocks the paper: the story just prints without a
picture. Article image URLs come from scraped pages, so every hop is checked to point at a public
host before it is fetched.
"""

import asyncio
import base64
import hashlib
import io
import ipaddress
import socket
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx
import structlog
from PIL import Image, ImageOps, UnidentifiedImageError

log = structlog.get_logger(__name__)

MAX_EDGE = 1200
MIN_EDGE = 200  # tracking pixels and icons are not pictures
MAX_DOWNLOAD_BYTES = 8 * 1024 * 1024
MAX_REDIRECTS = 3
TIMEOUT_SECONDS = 6.0
TOTAL_BUDGET_SECONDS = 8.0
CONCURRENCY = 6
JPEG_QUALITY = 80


async def is_public_url(url: str) -> bool:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return False
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(
            parts.hostname, None, type=socket.SOCK_STREAM
        )
    except OSError:
        return False
    return bool(infos) and all(ipaddress.ip_address(i[4][0]).is_global for i in infos)


def shrink(raw: bytes) -> bytes | None:
    """JPEG bytes within ``MAX_EDGE`` on the long side, or None if the data is unusable."""
    try:
        with Image.open(io.BytesIO(raw)) as opened:
            image: Image.Image = ImageOps.exif_transpose(opened)
            if min(image.size) < MIN_EDGE:
                return None
            if image.mode in ("RGBA", "LA", "P"):
                rgba = image.convert("RGBA")
                flat = Image.new("RGB", rgba.size, "white")
                flat.paste(rgba, mask=rgba.getchannel("A"))
                image = flat
            else:
                image = image.convert("RGB")
            image.thumbnail((MAX_EDGE, MAX_EDGE), Image.Resampling.LANCZOS)
            out = io.BytesIO()
            image.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            return out.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        return None


def data_uri(jpeg: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()


class ImageCache:
    def __init__(
        self,
        directory: Path,
        user_agent: str,
        *,
        client: httpx.AsyncClient | None = None,
        check_public: bool = True,
    ) -> None:
        self._dir = directory
        self._client = client or httpx.AsyncClient(
            timeout=TIMEOUT_SECONDS, headers={"User-Agent": user_agent, "Accept": "image/*"}
        )
        self._check_public = check_public

    def _path(self, url: str) -> Path:
        return self._dir / f"{hashlib.sha256(url.encode()).hexdigest()[:40]}.jpg"

    async def _download(self, url: str) -> bytes | None:
        for _ in range(MAX_REDIRECTS + 1):
            if self._check_public and not await is_public_url(url):
                log.info("image_skipped", url=url, reason="not a public http(s) url")
                return None
            async with self._client.stream("GET", url, follow_redirects=False) as response:
                if response.is_redirect and (location := response.headers.get("location")):
                    url = urljoin(url, location)
                    continue
                if response.is_error:
                    log.info("image_skipped", url=url, reason=f"HTTP {response.status_code}")
                    return None
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_DOWNLOAD_BYTES:
                        log.info("image_skipped", url=url, reason="too large")
                        return None
                return bytes(body)
        log.info("image_skipped", url=url, reason="too many redirects")
        return None

    async def fetch(self, url: str) -> str | None:
        """A data URI for the image at ``url``, or None when it cannot be used."""
        cached = self._path(url)
        if await asyncio.to_thread(cached.is_file):
            return data_uri(await asyncio.to_thread(cached.read_bytes))
        try:
            raw = await self._download(url)
        except (httpx.HTTPError, OSError) as exc:
            log.info("image_skipped", url=url, reason=type(exc).__name__)
            return None
        jpeg = await asyncio.to_thread(shrink, raw) if raw else None
        if jpeg is None:
            return None
        await asyncio.to_thread(self._store, cached, jpeg)
        return data_uri(jpeg)

    def _store(self, path: Path, jpeg: bytes) -> None:
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            path.write_bytes(jpeg)
        except OSError:
            log.warning("image_cache_write_failed", path=str(path))

    async def fetch_many(self, urls: Mapping[str, str]) -> dict[str, str]:
        """Fetch ``{key: url}`` concurrently within a time budget; keys that fail are absent."""
        found: dict[str, str] = {}
        if not urls:
            return found
        gate = asyncio.Semaphore(CONCURRENCY)

        async def one(key: str, url: str) -> None:
            async with gate:
                if uri := await self.fetch(url):
                    found[key] = uri

        tasks = [asyncio.create_task(one(k, u)) for k, u in urls.items()]
        _, pending = await asyncio.wait(tasks, timeout=TOTAL_BUDGET_SECONDS)
        for task in pending:
            task.cancel()
        if pending:
            log.warning("image_budget_exceeded", skipped=len(pending))
        return found

    async def aclose(self) -> None:
        await self._client.aclose()
