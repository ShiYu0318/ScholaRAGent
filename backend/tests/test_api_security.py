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
