"""通知偏好與提醒端點：離線。"""
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
                     json={"email": "n@b.c", "password": "password123"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


# ---- 通知偏好 ----
def test_preferences_defaults(api, auth):
    prefs = api.get("/api/notifications/preferences", headers=auth).json()
    assert prefs["frequency"] == "daily"
    assert prefs["hour"] == 9
    assert prefs["timezone"] == "Asia/Taipei"
    assert prefs["channels"] == ["web"]


def test_preferences_update_partial(api, auth):
    resp = api.put("/api/notifications/preferences",
                   json={"frequency": "weekly", "hour": 8,
                         "channels": ["web", "telegram"], "quiet_start": 22,
                         "quiet_end": 7},
                   headers=auth)
    assert resp.status_code == 200
    prefs = resp.json()
    assert prefs["frequency"] == "weekly" and prefs["hour"] == 8
    assert prefs["channels"] == ["web", "telegram"]
    # 未提供的欄位維持原值
    assert prefs["minute"] == 0
    again = api.get("/api/notifications/preferences", headers=auth).json()
    assert again["quiet_start"] == 22 and again["quiet_end"] == 7


def test_preferences_validation(api, auth):
    assert api.put("/api/notifications/preferences", json={"hour": 25},
                   headers=auth).status_code == 422
    assert api.put("/api/notifications/preferences", json={"frequency": "hourly"},
                   headers=auth).status_code == 422
    assert api.put("/api/notifications/preferences", json={"channels": ["pigeon"]},
                   headers=auth).status_code == 422


# ---- 提醒 ----
def test_reminders_crud(api, auth):
    created = api.post("/api/reminders",
                       json={"text": "重讀 RAG survey", "due_at": "2030-01-01T09:00:00",
                             "context": {"paper_id": "2401.00001"}},
                       headers=auth)
    assert created.status_code == 201
    rid = created.json()["id"]
    assert created.json()["done"] is False

    items = api.get("/api/reminders", headers=auth).json()["items"]
    assert [r["id"] for r in items] == [rid]

    assert api.post(f"/api/reminders/{rid}/complete", headers=auth).status_code == 200
    assert api.get("/api/reminders", headers=auth).json()["items"] == []
    done = api.get("/api/reminders", params={"include_done": True},
                   headers=auth).json()["items"]
    assert done[0]["done"] is True

    assert api.delete(f"/api/reminders/{rid}", headers=auth).status_code == 204
    assert api.delete(f"/api/reminders/{rid}", headers=auth).status_code == 404


def test_reminders_are_per_user(api, auth):
    rid = api.post("/api/reminders",
                   json={"text": "mine", "due_at": "2030-01-01T09:00:00"},
                   headers=auth).json()["id"]
    other = api.post("/auth/register",
                     json={"email": "n2@b.c", "password": "password123"}).json()["token"]
    other_auth = {"Authorization": f"Bearer {other}"}
    assert api.get("/api/reminders", headers=other_auth).json()["items"] == []
    assert api.post(f"/api/reminders/{rid}/complete",
                    headers=other_auth).status_code == 404
