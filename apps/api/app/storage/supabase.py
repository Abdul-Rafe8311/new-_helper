"""Supabase Storage over its REST API (service-key access to a private bucket)."""

from urllib.parse import quote

import httpx

from app.storage.base import StorageError, StorageNotFoundError

TIMEOUT_SECONDS = 30.0


class SupabaseStorage:
    def __init__(
        self,
        url: str,
        service_key: str,
        bucket: str,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base = f"{url.rstrip('/')}/storage/v1/object"
        self._bucket = bucket
        self._client = client or httpx.AsyncClient(timeout=TIMEOUT_SECONDS)
        self._headers = {"Authorization": f"Bearer {service_key}", "apikey": service_key}

    def _url(self, path: str) -> str:
        return f"{self._base}/{self._bucket}/{quote(path)}"

    async def put(self, path: str, data: bytes, content_type: str) -> None:
        response = await self._client.post(
            self._url(path),
            content=data,
            headers={**self._headers, "Content-Type": content_type, "x-upsert": "true"},
        )
        if response.is_error:
            raise StorageError(f"upload of {path!r} failed with HTTP {response.status_code}")

    async def get(self, path: str) -> bytes:
        response = await self._client.get(self._url(path), headers=self._headers)
        if response.status_code in (400, 404):  # Supabase answers 400 for a missing object
            raise StorageNotFoundError(path)
        if response.is_error:
            raise StorageError(f"download of {path!r} failed with HTTP {response.status_code}")
        return response.content

    async def exists(self, path: str) -> bool:
        try:
            await self.get(path)
        except StorageNotFoundError:
            return False
        return True
