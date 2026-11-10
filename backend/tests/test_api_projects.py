"""研究專案端點：CRUD、擁有者隔離、專案文獻。全離線。"""
import pytest
from fastapi.testclient import TestClient

from src import store as store_module
from src.store.sqlite_faiss import SqliteFaissStore

PAPERS = [{"id": f"p{i}", "title": f"Paper {i}", "abstract": "about retrieval",
           "link": f"https://arxiv.org/abs/p{i}", "published": "2026-01-01",
           "authors": "A. Author"} for i in range(1, 5)]


@pytest.fixture
def api(tmp_path, fake_embedder):
    from src.api.app import create_app

    store = SqliteFaissStore(db_path=tmp_path / "api.db", embedder=fake_embedder)
    store.upsert_papers(PAPERS)
    prev = store_module.set_store(store)
    client = TestClient(create_app())
    yield client
    store_module.set_store(prev)
    store.close()


def _user(api, email):
    token = api.post("/auth/register",
                     json={"email": email, "password": "password123"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth(api):
    return _user(api, "owner@example.com")


@pytest.fixture
def other(api):
    return _user(api, "other@example.com")


def _project(api, auth, name="RAG evaluation"):
    return api.post("/api/projects", headers=auth,
                    json={"name": name, "question": "How should RAG be evaluated?"}).json()


def test_project_lifecycle(api, auth):
    p = _project(api, auth)
    assert p["name"] == "RAG evaluation" and p["status"] == "active"
    assert [x["id"] for x in api.get("/api/projects", headers=auth).json()["items"]] == [p["id"]]

    upd = api.patch(f"/api/projects/{p['id']}", headers=auth,
                    json={"status": "archived"}).json()
    assert upd["status"] == "archived" and upd["name"] == "RAG evaluation"
    assert api.get("/api/projects", headers=auth).json()["items"] == []
    assert len(api.get("/api/projects?include_archived=true",
                       headers=auth).json()["items"]) == 1

    assert api.delete(f"/api/projects/{p['id']}", headers=auth).status_code == 204
    assert api.get(f"/api/projects/{p['id']}", headers=auth).status_code == 404


def test_projects_require_login(api):
    assert api.get("/api/projects").status_code == 401
    assert api.post("/api/projects", json={"name": "x"}).status_code == 401


def test_other_users_cannot_see_or_touch_a_project(api, auth, other):
    p = _project(api, auth)
    base = f"/api/projects/{p['id']}"
    assert api.get(base, headers=other).status_code == 404
    assert api.patch(base, headers=other, json={"name": "mine now"}).status_code == 404
    assert api.delete(base, headers=other).status_code == 404
    assert api.get(f"{base}/papers", headers=other).status_code == 404
    assert api.post(f"{base}/papers", headers=other,
                    json={"paper_ids": ["p1"]}).status_code == 404
    assert api.get("/api/projects", headers=other).json()["items"] == []
    assert api.get(base, headers=auth).json()["name"] == "RAG evaluation"


def test_project_papers_add_list_remove(api, auth):
    p = _project(api, auth)
    base = f"/api/projects/{p['id']}/papers"
    resp = api.post(base, headers=auth, json={"paper_ids": ["p1", "p2", "missing"]}).json()
    assert resp["added"] == 2 and resp["project"]["paper_count"] == 2

    api.post("/api/reading", headers=auth,
             json={"paper_id": "p1", "state": "reading", "note": "key paper", "tags": ["core"]})
    items = {x["id"]: x for x in api.get(base, headers=auth).json()["items"]}
    assert set(items) == {"p1", "p2"}
    assert items["p1"]["reading"] == {"state": "reading", "tags": ["core"], "note": "key paper"}
    assert items["p2"]["reading"] is None

    assert api.delete(f"{base}/p1", headers=auth).status_code == 204
    assert api.delete(f"{base}/p1", headers=auth).status_code == 404
    assert [x["id"] for x in api.get(base, headers=auth).json()["items"]] == ["p2"]


def test_project_validation_and_caps(api, auth, monkeypatch):
    from src.api.routers import projects
    assert api.post("/api/projects", headers=auth, json={"name": ""}).status_code == 422
    assert api.post("/api/projects", headers=auth, json={"name": "n" * 121}).status_code == 422
    p = _project(api, auth)
    assert api.patch(f"/api/projects/{p['id']}", headers=auth,
                     json={"status": "bogus"}).status_code == 422
    monkeypatch.setattr(projects, "MAX_PAPERS_PER_PROJECT", 1)
    assert api.post(f"/api/projects/{p['id']}/papers", headers=auth,
                    json={"paper_ids": ["p1", "p2"]}).status_code == 422
    monkeypatch.setattr(projects, "MAX_PROJECTS_PER_USER", 1)
    assert api.post("/api/projects", headers=auth, json={"name": "second"}).status_code == 422
