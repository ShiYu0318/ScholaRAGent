"""健康監控端點：統計、排程器狀態、金鑰布林（不洩漏值）。"""
import pytest
from fastapi.testclient import TestClient

from src import store as store_module
from src.store.sqlite_faiss import SqliteFaissStore


@pytest.fixture
def api(tmp_path, fake_embedder, isolated_data):
    from src.api.app import create_app

    store = SqliteFaissStore(db_path=tmp_path / "api.db", embedder=fake_embedder)
    prev_store = store_module.set_store(store)
    client = TestClient(create_app())
    yield client
    store_module.set_store(prev_store)
    store.close()


@pytest.fixture
def auth(api):
    token = api.post("/auth/register",
                     json={"email": "h@example.com", "password": "password123"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_shape_and_no_secret_leak(api, auth):
    resp = api.get("/api/health", headers=auth)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["store_backend"] in ("sqlite", "postgres")
    assert data["store"]["papers"] == 0
    # 測試環境不啟排程器
    assert data["scheduler"] == {"running": False, "jobs": []}
    # providers 只能是布林（金鑰值不得外洩）
    assert data["providers"] and all(
        isinstance(v, bool) for v in data["providers"].values())


def test_health_without_login_only_reports_liveness(api):
    # 無 Authorization 可讀（監控探針用），但不暴露組態與統計
    assert api.get("/api/health").json() == {"status": "ok", "version": "2.0.0"}


def test_health_with_invalid_token_is_treated_as_anonymous(api):
    data = api.get("/api/health", headers={"Authorization": "Bearer nope"}).json()
    assert set(data) == {"status", "version"}
