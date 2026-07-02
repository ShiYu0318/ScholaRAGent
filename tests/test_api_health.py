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


def test_health_shape_and_no_secret_leak(api):
    resp = api.get("/api/health")
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


def test_health_is_public(api):
    # 無 Authorization 也可讀（監控用），但不含任何使用者資料
    data = api.get("/api/health").json()
    assert "users" in data["store"]
