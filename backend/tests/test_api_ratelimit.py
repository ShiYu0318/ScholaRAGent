"""限流：滑動視窗行為與登入端點 429。"""
import pytest
from fastapi.testclient import TestClient

from src import config
from src import store as store_module
from src.api.ratelimit import RateLimiter
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


def test_limiter_allows_until_limit_then_reports_wait():
    now = [0.0]
    limiter = RateLimiter(clock=lambda: now[0])
    assert [limiter.hit("k", 2, 60) for _ in range(2)] == [0, 0]
    assert limiter.hit("k", 2, 60) >= 1
    now[0] = 61
    assert limiter.hit("k", 2, 60) == 0


def test_limiter_keys_are_independent():
    limiter = RateLimiter(clock=lambda: 0.0)
    assert limiter.hit("a", 1, 60) == 0
    assert limiter.hit("b", 1, 60) == 0
    assert limiter.hit("a", 1, 60) >= 1


def test_login_bruteforce_gets_429_with_retry_after(api):
    body = {"email": "u@example.com", "password": "wrong-password"}
    codes = [api.post("/auth/login", json=body).status_code
             for _ in range(config.RATE_LIMIT_LOGIN_PER_MIN)]
    assert set(codes) == {401}
    resp = api.post("/auth/login", json=body)
    assert resp.status_code == 429
    assert int(resp.headers["Retry-After"]) >= 1


def test_limit_can_be_disabled(api, monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMIT_ENABLED", False)
    body = {"email": "u@example.com", "password": "wrong-password"}
    for _ in range(config.RATE_LIMIT_LOGIN_PER_MIN + 3):
        assert api.post("/auth/login", json=body).status_code == 401
