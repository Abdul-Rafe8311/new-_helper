"""Choose the storage backend from settings."""

from app.core.config import Settings
from app.storage.base import Storage, StorageError
from app.storage.local import LocalStorage
from app.storage.supabase import SupabaseStorage


def get_storage(settings: Settings) -> Storage:
    if settings.storage_backend == "supabase":
        key = settings.supabase_service_key.get_secret_value()
        if not settings.supabase_url or not key:
            raise StorageError("SUPABASE_URL and SUPABASE_SERVICE_KEY are required for Supabase")
        return SupabaseStorage(settings.supabase_url, key, settings.supabase_bucket)
    return LocalStorage(settings.storage_local_dir)
