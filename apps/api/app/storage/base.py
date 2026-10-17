"""The storage protocol and its errors."""

from typing import Protocol


class StorageError(Exception):
    """The backend failed to store or fetch a file."""


class StorageNotFoundError(StorageError):
    """No file exists at the requested path."""


class Storage(Protocol):
    """Binary files addressed by slash-separated relative paths."""

    async def put(self, path: str, data: bytes, content_type: str) -> None:
        """Store ``data`` at ``path``, replacing any existing file."""

    async def get(self, path: str) -> bytes:
        """The file's bytes; raises ``StorageNotFoundError`` when there is none."""

    async def exists(self, path: str) -> bool:
        """Whether a file is stored at ``path``."""
