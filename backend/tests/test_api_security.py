"""資安強化：production 設定檢查、長密碼、標頭、body 上限、錯誤訊息。"""
import pytest
from fastapi.testclient import TestClient

from src import config
from src import store as store_module
from src.api import auth as auth_lib
from src.store.sqlite_faiss import SqliteFaissStore


@pytest.fixture
def api(tmp_path, fake_embedder):
    from src.api.app import create_app

    store = SqliteFaissStore(db_path=tmp_path / "api.db", embedder=fake_embedder)
    prev = store_module.set_store(store)
    client = TestClient(create_app())
    yield client
    store_module.set_store(prev)
    store.close()


def _token(api, email="u@example.com"):
    resp = api.post("/auth/register", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {resp.json()['token']}"}


# ---- production 設定 ----
def test_production_refuses_to_start_without_strong_secret(monkeypatch):
    from src.api.app import create_app
    monkeypatch.setattr(config, "APP_ENV", "production")
    monkeypatch.setattr(config, "JWT_SECRET", "")
    with pytest.raises(RuntimeError):
        create_app()
    monkeypatch.setattr(config, "JWT_SECRET", "short")
    with pytest.raises(RuntimeError):
        create_app()


def test_production_starts_with_strong_secret(monkeypatch):
    from src.api.app import create_app
    monkeypatch.setattr(config, "APP_ENV", "production")
    monkeypatch.setattr(config, "JWT_SECRET", "x" * 48)
    monkeypatch.setattr(config, "CORS_ORIGINS", ["https://app.example.com"])
    assert create_app() is not None


def test_production_rejects_wildcard_cors(monkeypatch):
    from src.api.app import create_app
    monkeypatch.setattr(config, "APP_ENV", "production")
    monkeypatch.setattr(config, "JWT_SECRET", "x" * 48)
    monkeypatch.setattr(config, "CORS_ORIGINS", ["*"])
    with pytest.raises(RuntimeError):
        create_app()


# ---- 密碼 ----
def test_long_password_hashes_and_verifies():
    long_pw = "é" * 100  # 200 bytes，超過 bcrypt 的 72 bytes
    hashed = auth_lib.hash_password(long_pw)
    assert auth_lib.verify_password(long_pw, hashed)
    assert not auth_lib.verify_password("é" * 99, hashed)


def test_register_with_long_multibyte_password_succeeds(api):
    resp = api.post("/auth/register",
                    json={"email": "long@example.com", "password": "密" * 60})
    assert resp.status_code == 201


# ---- 標頭 ----
def test_security_headers_on_api_responses(api):
    h = api.get("/api/health").headers
    assert h["x-content-type-options"] == "nosniff"
    assert h["x-frame-options"] == "DENY"
    assert h["referrer-policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in h["content-security-policy"]
    assert "script-src 'self'" in h["content-security-policy"]
    assert h["cache-control"] == "no-store"


def test_security_headers_on_error_responses(api):
    h = api.get("/auth/me").headers
    assert h["x-content-type-options"] == "nosniff"


def test_hsts_only_when_served_over_https(api, monkeypatch):
    assert "strict-transport-security" not in api.get("/api/health").headers
    monkeypatch.setattr(config, "API_PUBLIC_URL", "https://api.example.com")
    assert "max-age" in api.get("/api/health").headers["strict-transport-security"]


def test_docs_disabled_when_configured(monkeypatch, tmp_path, fake_embedder):
    from src.api.app import create_app
    monkeypatch.setattr(config, "API_DOCS_ENABLED", False)
    client = TestClient(create_app())
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


# ---- body 大小 ----
def test_oversized_body_rejected_with_413(api, monkeypatch):
    headers = _token(api)
    big = "x" * (config.MAX_BODY_BYTES + 10)
    resp = api.post("/api/memory", json={"content": big}, headers=headers)
    assert resp.status_code == 413
    assert resp.headers["x-content-type-options"] == "nosniff"


def test_oversized_chunked_body_rejected(api):
    headers = _token(api)

    def chunks():
        yield b'{"content": "'
        for _ in range(12):
            yield b"x" * (config.MAX_BODY_BYTES // 10)
        yield b'"}'

    resp = api.post("/api/memory", content=chunks(),
                    headers={**headers, "Content-Type": "application/json"})
    assert resp.status_code == 413


def test_normal_body_passes(api, tmp_path, monkeypatch):
    from src.api.routers import extras
    from src.memory.memory_store import MemoryStore
    prev = extras.set_memory(MemoryStore(path=tmp_path / "mem.json"))
    try:
        resp = api.post("/api/memory", json={"content": "hello"}, headers=_token(api))
        assert resp.status_code == 201
    finally:
        extras.set_memory(prev)


# ---- 未處理例外 ----
def test_unhandled_exception_returns_generic_500(tmp_path, fake_embedder, monkeypatch):
    from src.api.app import create_app
    from src.api.services import library as library_module

    store = SqliteFaissStore(db_path=tmp_path / "api.db", embedder=fake_embedder)
    prev = store_module.set_store(store)

    class Boom:
        def papers(self, **kwargs):
            raise RuntimeError("/srv/secret/path/key.pem not found")

    prev_service = library_module.set_library_service(Boom())
    try:
        client = TestClient(create_app(), raise_server_exceptions=False)
        resp = client.get("/api/papers", headers=_token(client))
        assert resp.status_code == 500
        assert resp.json() == {"detail": "伺服器內部錯誤"}
        assert "secret" not in resp.text
    finally:
        library_module.set_library_service(prev_service)
        store_module.set_store(prev)
        store.close()
