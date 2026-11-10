"""輸入驗證：長度/數量上限與格式檢查，超出一律 422。"""
import pytest
from fastapi.testclient import TestClient

from src import store as store_module
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


@pytest.fixture
def auth(api):
    token = api.post("/auth/register",
                     json={"email": "v@example.com", "password": "password123"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("path,body", [
    ("/api/reading", {"paper_id": "p", "note": "n" * 5001}),
    ("/api/reading", {"paper_id": "p", "tags": ["t"] * 21}),
    ("/api/reading", {"paper_id": "p", "tags": ["x" * 41]}),
    ("/api/reading", {"paper_id": "p", "state": "bogus"}),
    ("/api/reading", {"paper_id": "p" * 201}),
    ("/api/reminders", {"text": "t", "due_at": "not-a-date-at-all"}),
    ("/api/reminders", {"text": "t", "due_at": "2026-07-03T09:00:00",
                        "context": {"blob": "x" * 3000}}),
    ("/api/interactions", {"action": "DROP TABLE", "paper_id": "p"}),
    ("/api/interactions", {"action": "like", "paper_id": "p", "value": 1e9}),
    ("/api/explain", {"paper_id": ""}),
    ("/api/explain", {"nope": 1}),
    ("/api/compare", {"paper_ids": ["p"] * 21}),
    ("/api/memory", {"content": "c", "kind": "Bad Kind!"}),
    ("/api/subscriptions", {"name": "n", "keywords": ["k"] * 21}),
    ("/api/eval", {"engine": "judge", "question": "q", "answer": "a",
                   "contexts": ["c"] * 21}),
])
def test_oversized_or_malformed_bodies_rejected(api, auth, path, body):
    assert api.post(path, json=body, headers=auth).status_code == 422


@pytest.mark.parametrize("path", [
    "/api/papers?limit=0", "/api/papers?limit=100000",
    "/api/papers?query=" + "q" * 201,
    "/api/conversations?limit=-1",
    "/api/memory?limit=100000",
    "/api/daily/personalized?top_n=1000",
    "/api/reading?state=bogus",
    "/api/graph/global?query=" + "q" * 501,
])
def test_query_parameters_are_bounded(api, auth, path):
    assert api.get(path, headers=auth).status_code == 422


def test_notification_timezone_must_be_real(api, auth):
    bad = api.put("/api/notifications/preferences", json={"timezone": "Mars/Olympus"},
                  headers=auth)
    assert bad.status_code == 422
    ok = api.put("/api/notifications/preferences", json={"timezone": "Asia/Taipei"},
                 headers=auth)
    assert ok.status_code == 200


def test_learning_path_update_size_is_bounded(api, auth):
    resp = api.patch("/api/learning-paths/1", headers=auth,
                     json={"items": [{"title": "x" * 1000} for _ in range(51)]})
    assert resp.status_code == 422
    resp = api.patch("/api/learning-paths/1", headers=auth,
                     json={"progress": {"k": "x" * 9000}})
    assert resp.status_code == 422


def test_profile_fields_are_bounded(api, auth):
    assert api.patch("/auth/me", json={"display_name": "n" * 81},
                     headers=auth).status_code == 422
    assert api.patch("/auth/me", json={"locale": "<script>"},
                     headers=auth).status_code == 422
    assert api.patch("/auth/me", json={"locale": "zh-TW"}, headers=auth).status_code == 200


def test_valid_reminder_and_reading_still_work(api, auth):
    r = api.post("/api/reminders", headers=auth,
                 json={"text": "讀論文", "due_at": "2026-12-01T09:00:00Z",
                       "context": {"paper_id": "p1"}})
    assert r.status_code == 201
    rd = api.post("/api/reading", headers=auth,
                  json={"paper_id": "p1", "title": "T", "tags": ["rag"], "note": "ok"})
    assert rd.status_code == 201
