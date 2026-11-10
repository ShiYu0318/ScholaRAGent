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


# ---- 總覽 ----
def test_overview_walks_through_the_research_stages(api, auth):
    p = _project(api, auth)
    base = f"/api/projects/{p['id']}"

    def overview():
        return api.get(f"{base}/overview", headers=auth).json()

    assert overview()["next_step"] == "collect"

    api.post(f"{base}/papers", headers=auth, json={"paper_ids": ["p1", "p2", "p3"]})
    o = overview()
    assert o["next_step"] == "read"
    assert o["stages"]["collect"] == {"count": 3, "done": True}
    assert o["stages"]["read"]["to_read"] == 3

    api.post("/api/reading", headers=auth, json={"paper_id": "p1", "state": "done"})
    api.post("/api/reading", headers=auth, json={"paper_id": "p2", "state": "reading"})
    o = overview()
    assert o["next_step"] == "ask"
    assert (o["stages"]["read"]["done"], o["stages"]["read"]["reading"],
            o["stages"]["read"]["to_read"], o["stages"]["read"]["total"]) == (True, 1, 1, 3)
    assert o["stages"]["read"]["count"] == 1

    store = store_module.get_store()
    user_id = store.get_user_by_email("owner@example.com")["id"]
    store.create_conversation(user_id, title="Q1", project_id=p["id"])
    assert overview()["next_step"] == "synthesize"

    api.post("/api/documents", headers=auth,
             json={"title": "Survey", "kind": "review", "project_id": p["id"]})
    assert overview()["next_step"] == "write"

    api.post("/api/documents", headers=auth,
             json={"title": "Paper draft", "kind": "draft", "project_id": p["id"]})
    o = overview()
    assert o["next_step"] == "export"
    assert all(stage["done"] for stage in o["stages"].values())
    assert [d["title"] for d in o["recent_documents"]] == ["Paper draft", "Survey"]
    assert o["recent_conversations"][0]["title"] == "Q1"


def test_overview_is_owner_only(api, auth, other):
    p = _project(api, auth)
    assert api.get(f"/api/projects/{p['id']}/overview", headers=other).status_code == 404
    assert api.get(f"/api/projects/{p['id']}/export", headers=other).status_code == 404


# ---- 匯出 ----
def test_export_bundles_references_notes_and_documents(api, auth):
    import io
    import zipfile

    p = _project(api, auth, name="RAG 評估 / eval")
    base = f"/api/projects/{p['id']}"
    api.post(f"{base}/papers", headers=auth, json={"paper_ids": ["p1", "p2"]})
    api.post("/api/reading", headers=auth,
             json={"paper_id": "p1", "state": "done", "tags": ["core"], "note": "關鍵論文"})
    for title in ("Survey", "Survey", "../../escape"):
        api.post("/api/documents", headers=auth,
                 json={"title": title, "content": "body", "kind": "review",
                       "project_id": p["id"], "paper_ids": ["p1"]})
    api.post("/api/documents", headers=auth, json={"title": "not in project"})

    resp = api.get(f"{base}/export", headers=auth)
    assert resp.status_code == 200 and resp.headers["content-type"] == "application/zip"
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    names = zf.namelist()
    assert {"README.md", "references.bib", "notes.md"} <= set(names)
    docs = [n for n in names if n.startswith("documents/")]
    assert len(docs) == 3 and len(set(docs)) == 3
    assert all(".." not in n and not n.startswith("/") for n in names)   # 無路徑穿越

    assert zf.read("references.bib").decode().count("@misc{") == 2
    notes = zf.read("notes.md").decode()
    assert "關鍵論文" in notes and "Tags: core" in notes and "Status: done" in notes
    readme = zf.read("README.md").decode()
    assert "How should RAG be evaluated?" in readme and "Paper 1" in readme
    assert "## References" in zf.read(docs[0]).decode()
