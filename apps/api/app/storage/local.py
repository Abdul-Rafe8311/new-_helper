"""Local-disk storage for development and tests."""

import asyncio
from pathlib import Path

from app.storage.base import StorageError, StorageNotFoundError


class LocalStorage:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()

    def _resolve(self, path: str) -> Path:
        target = (self.root / path).resolve()
        if not target.is_relative_to(self.root):
            raise StorageError(f"path escapes the storage root: {path!r}")
        return target

    async def put(self, path: str, data: bytes, content_type: str) -> None:
        target = self._resolve(path)

        def write() -> None:
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_name(target.name + ".tmp")
            tmp.write_bytes(data)
            tmp.replace(target)  # readers never see a half-written file

        await asyncio.to_thread(write)

    async def get(self, path: str) -> bytes:
        target = self._resolve(path)
        try:
            return await asyncio.to_thread(target.read_bytes)
        except FileNotFoundError as exc:
            raise StorageNotFoundError(path) from exc

    async def exists(self, path: str) -> bool:
        return await asyncio.to_thread(self._resolve(path).is_file)
