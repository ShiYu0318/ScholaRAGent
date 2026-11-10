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

    def search_topic(self, topic, limit=8):
        return [dict(p) for p in ARXIV_PAPERS[:limit]]

    def fetch_by_ids(self, ids):
        known = {p["id"]: p for p in ARXIV_PAPERS}
        return [dict(known[i]) for i in ids if i in known]


class StubNews:
    def fetch_feed(self, url, timeout=10):
        return [{"id": "rss-1", "title": "AI News", "abstract": "news body",
                 "authors": "", "link": "http://n/1", "published": "2026-07-01",
                 "source": "news"}]


class StubOpenAlex:
    def work_by_arxiv(self, arxiv_id, title=None):
        return {"cited_by_count": 150}

    def paper_by_doi(self, doi):
        if doi != "10.1000/known":
            return None
        return {"id": f"doi:{doi}", "title": "DOI Paper", "abstract": "abs", "authors": "C",
                "link": "https://doi.org/10.1000/known", "published": "2020-01-01",
                "source": "doi"}


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


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:8000/rss", "http://localhost/rss", "http://169.254.169.254/latest",
    "http://10.0.0.8/feed.xml", "http://db.internal/feed", "http://[::1]/rss",
])
def test_feed_url_pointing_inside_the_network_is_rejected(api, auth, url):
    assert api.post("/api/feeds", json={"url": url}, headers=auth).status_code == 422


def test_feed_count_is_capped_per_user(api, auth, monkeypatch):
    from src.api.routers import feeds
    monkeypatch.setattr(feeds, "MAX_FEEDS_PER_USER", 2)
    for i in range(2):
        assert api.post("/api/feeds", json={"url": f"https://example.com/{i}"},
                        headers=auth).status_code == 201
    assert api.post("/api/feeds", json={"url": "https://example.com/x"},
                    headers=auth).status_code == 422


def test_reading_note_and_tags_can_be_updated_independently(api, auth):
    api.post("/api/reading", headers=auth,
             json={"paper_id": "p1", "title": "T", "tags": ["rag"], "note": "first"})
    assert api.patch("/api/reading/p1", headers=auth, json={"note": "second"}).status_code == 200
    item = api.get("/api/reading", headers=auth).json()["items"][0]
    assert (item["note"], item["tags"], item["state"]) == ("second", ["rag"], "to-read")

    api.patch("/api/reading/p1", headers=auth, json={"tags": ["a", "b"], "state": "done"})
    item = api.get("/api/reading", headers=auth).json()["items"][0]
    assert (item["note"], item["tags"], item["state"]) == ("second", ["a", "b"], "done")
    assert api.patch("/api/reading/nope", headers=auth, json={"note": "x"}).status_code == 404
    assert api.patch("/api/reading/p1", headers=auth, json={"state": "bogus"}).status_code == 422


def test_paper_ids_with_slashes_are_routable(api, auth):
    api.post("/api/reading", headers=auth, json={"paper_id": "cs/0301001", "title": "Old"})
    assert api.patch("/api/reading/cs/0301001", headers=auth,
                     json={"state": "reading"}).status_code == 200
    assert api.delete("/api/reading/cs/0301001", headers=auth).status_code == 204


def test_discover_marks_papers_already_in_library(api, auth):
    api.post("/api/papers/import", headers=auth, json={"refs": ["2401.00001"]})
    items = api.get("/api/discover?query=graph networks", headers=auth).json()["items"]
    assert {p["id"]: p["in_library"] for p in items} == {"2401.00001": True,
                                                         "2401.00002": False}
    # 搜尋本身不入庫
    assert api.get("/api/papers", headers=auth).json()["total"] == 1


def test_import_by_arxiv_id_url_and_doi(api, auth):
    resp = api.post("/api/papers/import", headers=auth, json={"refs": [
        "2401.00001", "https://arxiv.org/abs/2401.00002", "10.1000/known",
        "10.1000/unknown", "not an id", "9999.99999"]}).json()
    assert [p["id"] for p in resp["imported"]] == ["2401.00001", "2401.00002",
                                                   "doi:10.1000/known"]
    assert set(resp["failed"]) == {"10.1000/unknown", "not an id", "9999.99999"}
    assert api.get("/api/papers", headers=auth).json()["total"] == 3
    assert api.get("/api/paper/doi:10.1000/known", headers=auth).json()["title"] == "DOI Paper"


def test_import_into_project_and_reading_list(api, auth):
    project = api.post("/api/projects", headers=auth, json={"name": "P"}).json()
    api.post("/api/papers/import", headers=auth,
             json={"refs": ["2401.00001"], "project_id": project["id"],
                   "add_to_reading": True})
    papers = api.get(f"/api/projects/{project['id']}/papers", headers=auth).json()["items"]
    assert [p["id"] for p in papers] == ["2401.00001"]
    assert papers[0]["reading"]["state"] == "to-read"
    # 再匯入一次不會把已有的閱讀狀態蓋掉
    api.patch("/api/reading/2401.00001", headers=auth, json={"state": "done"})
    api.post("/api/papers/import", headers=auth,
             json={"refs": ["2401.00001"], "add_to_reading": True})
    assert api.get("/api/reading", headers=auth).json()["items"][0]["state"] == "done"


def test_import_into_someone_elses_project_is_rejected(api, auth):
    other = api.post("/auth/register",
                     json={"email": "x@b.c", "password": "password123"}).json()["token"]
    project = api.post("/api/projects", json={"name": "theirs"},
                       headers={"Authorization": f"Bearer {other}"}).json()
    resp = api.post("/api/papers/import", headers=auth,
                    json={"refs": ["2401.00001"], "project_id": project["id"]})
    assert resp.status_code == 404
    assert api.get("/api/papers", headers=auth).json()["total"] == 0


def test_import_and_discover_validation(api, auth):
    assert api.post("/api/papers/import", headers=auth, json={"refs": []}).status_code == 422
    assert api.post("/api/papers/import", headers=auth,
                    json={"refs": ["1"] * 26}).status_code == 422
    assert api.get("/api/discover?query=a", headers=auth).status_code == 422
    assert api.get("/api/discover?query=rag&limit=100", headers=auth).status_code == 422
