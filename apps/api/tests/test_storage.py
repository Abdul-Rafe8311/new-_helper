import httpx
import pytest
import respx

from app.core.config import Settings
from app.storage import (
    LocalStorage,
    StorageError,
    StorageNotFoundError,
    SupabaseStorage,
    get_storage,
)


async def test_local_round_trip(tmp_path):
    storage = LocalStorage(tmp_path)
    assert not await storage.exists("editions/u/2026-10-17.pdf")
    await storage.put("editions/u/2026-10-17.pdf", b"%PDF", "application/pdf")
    assert await storage.exists("editions/u/2026-10-17.pdf")
    assert await storage.get("editions/u/2026-10-17.pdf") == b"%PDF"
    await storage.put("editions/u/2026-10-17.pdf", b"v2", "application/pdf")  # overwrite
    assert await storage.get("editions/u/2026-10-17.pdf") == b"v2"


async def test_local_missing_and_traversal(tmp_path):
    storage = LocalStorage(tmp_path)
    with pytest.raises(StorageNotFoundError):
        await storage.get("nope.pdf")
    with pytest.raises(StorageError):
        await storage.put("../escape.pdf", b"x", "application/pdf")


@respx.mock
async def test_supabase_put_get_exists():
    base = "https://proj.supabase.co/storage/v1/object/editions/editions/u/d.pdf"
    upload = respx.post(base).mock(return_value=httpx.Response(200, json={"Key": "k"}))
    respx.get(base).mock(return_value=httpx.Response(200, content=b"%PDF"))
    storage = SupabaseStorage("https://proj.supabase.co/", "service-key", "editions")
    await storage.put("editions/u/d.pdf", b"%PDF", "application/pdf")
    sent = upload.calls.last.request
    assert sent.headers["authorization"] == "Bearer service-key"
    assert sent.headers["x-upsert"] == "true"
    assert await storage.get("editions/u/d.pdf") == b"%PDF"
    assert await storage.exists("editions/u/d.pdf")


@respx.mock
async def test_supabase_errors():
    base = "https://proj.supabase.co/storage/v1/object/editions"
    respx.get(f"{base}/missing.pdf").mock(return_value=httpx.Response(400, json={}))
    respx.post(f"{base}/bad.pdf").mock(return_value=httpx.Response(500))
    storage = SupabaseStorage("https://proj.supabase.co", "k", "editions")
    assert not await storage.exists("missing.pdf")
    with pytest.raises(StorageError):
        await storage.put("bad.pdf", b"x", "application/pdf")


def test_factory_picks_backend(tmp_path):
    assert isinstance(get_storage(Settings(storage_local_dir=str(tmp_path))), LocalStorage)
    with pytest.raises(StorageError):
        get_storage(Settings(storage_backend="supabase"))
    configured = Settings(
        storage_backend="supabase", supabase_url="https://p.supabase.co", supabase_service_key="k"
    )
    assert isinstance(get_storage(configured), SupabaseStorage)
