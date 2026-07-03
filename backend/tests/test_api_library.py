"""文庫/feeds 端點：離線（stub 爬蟲與 OpenAlex、假 embedder）。"""
import pytest
from fastapi.testclient import TestClient

from src import store as store_module
from src.api.services import library as library_module
from src.api.services.library import LibraryService
from src.store.sqlite_faiss import SqliteFaissStore

ARXIV_PAPERS = [
    {"id": "2401.00001", "title": "GNN Survey", "abstract": "graph neural networks",
     "authors": "A", "link": "http://x/1", "published": "2026-06-30", "source": "arxiv"},
    {"id": "2401.00002", "title": "Diffusion Models", "abstract": "code: https://github.com/x/y",
     "authors": "B", "link": "http://x/2", "published": "2026-07-01", "source": "arxiv"},
]


class StubArxiv:
    def fetch_latest_papers(self, limit=5):
        return ARXIV_PAPERS[:limit]


class StubNews:
    def fetch_feed(self, url, timeout=10):
        return [{"id": "rss-1", "title": "AI News", "abstract": "news body",
                 "authors": "", "link": "http://n/1", "published": "2026-07-01",
                 "source": "news"}]


class StubOpenAlex:
    def work_by_arxiv(self, arxiv_id, title=None):
        return {"cited_by_count": 150}


@pytest.fixture
def api(tmp_path, fake_embedder, isolated_data):
    from src.api.app import create_app

    store = SqliteFaissStore(db_path=tmp_path / "api.db", embedder=fake_embedder)
    service = LibraryService(store, arxiv=StubArxiv(), news=StubNews(),
                             openalex=StubOpenAlex(), embedder=fake_embedder)
    prev_store = store_module.set_store(store)
    prev_service = library_module.set_library_service(service)
    client = TestClient(create_app())
    yield client
    library_module.set_library_service(prev_service)
    store_module.set_store(prev_store)
    store.close()


@pytest.fixture
def auth(api):
    token = api.post("/auth/register",
                     json={"email": "l@b.c", "password": "password123"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_daily_fetch_persists_and_indexes(api, auth):
    resp = api.post("/api/daily", json={}, headers=auth)
    assert resp.status_code == 200
    data = resp.json()
    assert data["fetched"] == 2 and data["added"] == 2
    # 再抓一次：去重，不再新增
    assert api.post("/api/daily", json={}, headers=auth).json()["added"] == 0


def test_papers_list_query_and_reproducibility(api, auth):
    api.post("/api/daily", json={}, headers=auth)
    items = api.get("/api/papers", headers=auth).json()["items"]
    assert len(items) == 2
    by_id = {p["id"]: p for p in items}
    assert by_id["2401.00002"]["reproducibility"]["has_code"] is True
    assert by_id["2401.00001"]["reproducibility"]["has_code"] is False

    hits = api.get("/api/papers", params={"query": "diffusion"}, headers=auth).json()
    assert hits["total"] == 1 and hits["items"][0]["id"] == "2401.00002"


def test_paper_detail_with_credibility(api, auth):
    api.post("/api/daily", json={}, headers=auth)
    p = api.get("/api/paper/2401.00001", headers=auth).json()
    assert p["credibility"] == {"cited_by_count": 150, "tier": "high"}
    assert api.get("/api/paper/nope", headers=auth).status_code == 404


def test_interactions_and_personalized(api, auth):
    api.post("/api/daily", json={}, headers=auth)
    resp = api.post("/api/interactions",
                    json={"action": "like", "paper_id": "2401.00001"}, headers=auth)
    assert resp.status_code == 201
    items = api.get("/api/daily/personalized", headers=auth).json()["items"]
    assert items[0]["id"] == "2401.00001"  # 按讚 GNN -> GNN 論文排最前


def test_reading_kanban_flow(api, auth):
    api.post("/api/daily", json={}, headers=auth)
    add = api.post("/api/reading", json={"paper_id": "2401.00001"}, headers=auth)
    assert add.status_code == 201
    assert add.json()["title"] == "GNN Survey"  # 未給標題時自動帶入

    api.patch("/api/reading/2401.00001", json={"state": "reading"}, headers=auth)
    items = api.get("/api/reading", params={"state": "reading"}, headers=auth).json()["items"]
    assert len(items) == 1
    assert api.patch("/api/reading/2401.00001", json={"state": "bogus"},
                     headers=auth).status_code == 422
    assert api.delete("/api/reading/2401.00001", headers=auth).status_code == 204


def test_feeds_crud_and_refresh(api, auth):
    feed = api.post("/api/feeds", json={"url": "https://example.com/rss"}, headers=auth)
    assert feed.status_code == 201
    dup = api.post("/api/feeds", json={"url": "https://example.com/rss"}, headers=auth)
    assert dup.status_code == 409

    refreshed = api.post("/api/feeds/refresh", headers=auth).json()
    assert refreshed == {"feeds": 1, "fetched": 1, "added": 1}
    items = api.get("/api/papers", params={"source": "rss"}, headers=auth).json()["items"]
    assert items[0]["id"] == "rss-1"

    fid = feed.json()["id"]
    updated = api.patch(f"/api/feeds/{fid}", json={"enabled": False}, headers=auth).json()
    assert updated["enabled"] is False
    assert api.post("/api/feeds/refresh", headers=auth).json()["feeds"] == 0
    assert api.delete(f"/api/feeds/{fid}", headers=auth).status_code == 204


def test_subscriptions_crud(api, auth):
    resp = api.post("/api/subscriptions",
                    json={"name": "gnn", "keywords": ["graph", "GNN"]}, headers=auth)
    assert resp.status_code == 201
    items = api.get("/api/subscriptions", headers=auth).json()["items"]
    assert items[0]["keywords"] == ["graph", "gnn"]
    assert api.delete("/api/subscriptions/gnn", headers=auth).status_code == 204
    assert api.delete("/api/subscriptions/gnn", headers=auth).status_code == 404


def test_exports(api, auth):
    api.post("/api/daily", json={}, headers=auth)
    csv_resp = api.get("/api/export/csv", headers=auth)
    assert csv_resp.headers["content-type"].startswith("text/csv")
    assert "GNN Survey" in csv_resp.text

    bib = api.get("/api/export/bibtex", headers=auth)
    assert "@" in bib.text

    zip_resp = api.get("/api/export/obsidian", headers=auth)
    assert zip_resp.headers["content-type"] == "application/zip"
    import io
    import zipfile
    zf = zipfile.ZipFile(io.BytesIO(zip_resp.content))
    assert any(n.endswith(".md") for n in zf.namelist())


def test_library_requires_auth(api):
    assert api.get("/api/papers").status_code == 401
    assert api.post("/api/daily", json={}).status_code == 401
