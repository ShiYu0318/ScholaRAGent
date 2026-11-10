"""文件端點：CRUD、擁有者隔離、匯出。全離線。"""
import pytest
from fastapi.testclient import TestClient

from src import store as store_module
from src.api.routers.documents import safe_filename
from src.store.sqlite_faiss import SqliteFaissStore

PAPERS = [{"id": "p1", "title": "Graph RAG", "abstract": "a", "authors": "Ada Lovelace",
           "link": "https://arxiv.org/abs/p1", "published": "2026-01-01"},
          {"id": "p2", "title": "Dense Retrieval", "abstract": "b", "authors": "Alan Turing",
           "link": "https://arxiv.org/abs/p2", "published": "2025-05-01"}]


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


def _doc(api, auth, **extra):
    body = {"title": "Related work", "content": "## Intro\nRAG [1] and retrieval [2].",
            "kind": "review", "paper_ids": ["p1", "p2"], **extra}
    resp = api.post("/api/documents", headers=auth, json=body)
    assert resp.status_code == 201
    return resp.json()


def test_document_lifecycle(api, auth):
    doc = _doc(api, auth)
    full = api.get(f"/api/documents/{doc['id']}", headers=auth).json()
    assert full["content"].startswith("## Intro")
    assert [p["id"] for p in full["papers"]] == ["p1", "p2"]

    listed = api.get("/api/documents", headers=auth).json()["items"]
    assert len(listed) == 1 and "content" not in listed[0] and listed[0]["excerpt"]

    upd = api.patch(f"/api/documents/{doc['id']}", headers=auth,
                    json={"content": "rewritten", "kind": "draft"}).json()
    assert upd["content"] == "rewritten" and upd["kind"] == "draft"
    assert upd["title"] == "Related work" and upd["paper_ids"] == ["p1", "p2"]

    assert api.delete(f"/api/documents/{doc['id']}", headers=auth).status_code == 204
    assert api.get(f"/api/documents/{doc['id']}", headers=auth).status_code == 404


def test_documents_belong_to_projects_and_can_be_moved_out(api, auth):
    project = api.post("/api/projects", headers=auth, json={"name": "P"}).json()
    doc = _doc(api, auth, project_id=project["id"])
    _doc(api, auth, title="loose note")
    scoped = api.get(f"/api/documents?project_id={project['id']}", headers=auth).json()["items"]
    assert [d["id"] for d in scoped] == [doc["id"]]
    assert api.get(f"/api/projects/{project['id']}", headers=auth).json()["document_count"] == 1

    moved = api.patch(f"/api/documents/{doc['id']}", headers=auth,
                      json={"project_id": None}).json()
    assert moved["project_id"] is None
    # 沒帶 project_id 的更新不會動到歸屬
    api.patch(f"/api/documents/{doc['id']}", headers=auth, json={"project_id": project["id"]})
    kept = api.patch(f"/api/documents/{doc['id']}", headers=auth, json={"title": "t2"}).json()
    assert kept["project_id"] == project["id"]


def test_other_users_cannot_access_documents(api, auth):
    doc = _doc(api, auth)
    other = _user(api, "other@example.com")
    base = f"/api/documents/{doc['id']}"
    assert api.get(base, headers=other).status_code == 404
    assert api.patch(base, headers=other, json={"title": "x"}).status_code == 404
    assert api.delete(base, headers=other).status_code == 404
    assert api.get(f"{base}/export", headers=other).status_code == 404
    assert api.get("/api/documents", headers=other).json()["items"] == []
    project = api.post("/api/projects", headers=auth, json={"name": "P"}).json()
    assert api.post("/api/documents", headers=other,
                    json={"title": "t", "project_id": project["id"]}).status_code == 404


def test_export_markdown_and_bibtex(api, auth):
    doc = _doc(api, auth, title="相關研究 / Related: work?")
    md = api.get(f"/api/documents/{doc['id']}/export", headers=auth)
    assert md.headers["content-type"].startswith("text/markdown")
    assert "attachment" in md.headers["content-disposition"]
    assert "\n" not in md.headers["content-disposition"]
    assert "## References" in md.text
    assert "1. Ada Lovelace. Graph RAG (2026). <https://arxiv.org/abs/p1>" in md.text

    bib = api.get(f"/api/documents/{doc['id']}/export?format=bib", headers=auth)
    assert bib.text.count("@misc{") == 2
    assert api.get(f"/api/documents/{doc['id']}/export?format=exe",
                   headers=auth).status_code == 422


def test_document_validation(api, auth):
    assert api.post("/api/documents", headers=auth, json={"title": ""}).status_code == 422
    assert api.post("/api/documents", headers=auth,
                    json={"title": "t", "kind": "bogus"}).status_code == 422
    assert api.post("/api/documents", headers=auth,
                    json={"title": "t", "content": "x" * 200_001}).status_code == 422
    assert api.post("/api/documents", headers=auth,
                    json={"title": "t", "project_id": 9999}).status_code == 404


@pytest.mark.parametrize("title,expected", [
    ("Related work", "Related-work"), ("../../etc/passwd", "etc-passwd"),
    ('a"b\r\nSet-Cookie: x', "a-b-Set-Cookie-x"), ("相關研究", "相關研究"), ("///", "document"),
])
def test_safe_filename(title, expected):
    assert safe_filename(title) == expected
