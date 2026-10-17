"""File storage behind one interface: local disk in dev, Supabase Storage in prod."""

from app.storage.base import Storage, StorageError, StorageNotFoundError
from app.storage.factory import get_storage
from app.storage.local import LocalStorage
from app.storage.supabase import SupabaseStorage

__all__ = [
    "LocalStorage",
    "Storage",
    "StorageError",
    "StorageNotFoundError",
    "SupabaseStorage",
    "get_storage",
]
