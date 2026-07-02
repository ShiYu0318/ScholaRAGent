"""洞察端點（趨勢/週報/分析）：離線（stub LLM、假 embedder）。"""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from src import store as store_module
from src.api.services import product as product_module
from src.api.services.product import ProductService
from src.store.sqlite_faiss import SqliteFaissStore


class StubLLM:
    def _chat(self, system, user, **kwargs):
        return "本週研究聚焦於 transformer 與檢索增強生成。"


def _paper(pid, title, abstract, published):
    return {"id": pid, "title": title, "abstract": abstract, "authors": "A",
            "link": f"http://x/{pid}", "published": published, "source": "arxiv"}


# 三個月遞增的 transformer 論文（趨勢偵測需要跨桶且上升）
TREND_PAPERS = [
    _paper("t1", "Transformer Basics", "transformer attention", "2026-04-10"),
    _paper("t2", "Transformer Scaling", "transformer scaling laws", "2026-05-05"),
    _paper("t3", "Transformer Memory", "transformer efficient memory", "2026-05-20"),
    _paper("t4", "Transformer Agents", "transformer agent planning", "2026-06-01"),
    _paper("t5", "Transformer Robotics", "transformer robotics control", "2026-06-15"),
    _paper("t6", "Transformer Reasoning", "transformer reasoning chains", "2026-06-28"),
]


@pytest.fixture
def api(tmp_path, fake_embedder, isolated_data):
    from src.api.app import create_app

    store = SqliteFaissStore(db_path=tmp_path / "api.db", embedder=fake_embedder)
    prev_store = store_module.set_store(store)
    prev_service = product_module.set_product_service(
        ProductService(store, llm=StubLLM()))
    client = TestClient(create_app())
    yield client, store
    product_module.set_product_service(prev_service)
    store_module.set_store(prev_store)
    store.close()


@pytest.fixture
def auth(api):
    client, _ = api
    token = client.post("/auth/register",
                        json={"email": "i@b.c", "password": "password123"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_requires_auth(api):
    client, _ = api
    assert client.get("/api/trends").status_code == 401
    assert client.get("/api/digest/weekly").status_code == 401
    assert client.get("/api/analytics").status_code == 401


def test_trends_rising_and_top(api, auth):
    client, store = api
    store.upsert_papers(TREND_PAPERS)
    data = client.get("/api/trends", headers=auth).json()
    assert data["total_papers"] == 6
    rising = {r["keyword"]: r for r in data["rising"]}
    assert "transformer" in rising
    assert rising["transformer"]["slope"] > 0
    assert rising["transformer"]["forecast"] >= 0
    top = {t["keyword"]: t["count"] for t in data["top"]}
    assert top["transformer"] == 6


def test_keyword_series(api, auth):
    client, store = api
    store.upsert_papers(TREND_PAPERS)
    data = client.get("/api/trends/transformer", headers=auth).json()
    assert sum(data["counts"]) == 6
    assert data["periods"] == sorted(data["periods"])
    # 未知關鍵字：空序列而非錯誤
    empty = client.get("/api/trends/zzznope", headers=auth).json()
    assert empty["counts"] == []


def test_weekly_digest_with_recent_papers(api, auth):
    client, store = api
    today = date.today()
    store.upsert_papers([
        _paper("w1", "Fresh RAG", "retrieval augmented", (today - timedelta(days=1)).isoformat()),
        _paper("w2", "Fresh Agents", "agent tools", today.isoformat()),
        _paper("old", "Ancient", "old topic", "2020-01-01"),
    ])
    data = client.get("/api/digest/weekly", headers=auth).json()
    assert data["window"] == "week"
    assert data["total"] == 2
    ids = {p["id"] for p in data["papers"]}
    assert ids == {"w1", "w2"}
    assert "transformer" in data["overview"] or data["overview"]


def test_weekly_digest_falls_back_to_latest(api, auth):
    client, store = api
    store.upsert_papers([_paper("old", "Ancient", "old topic", "2020-01-01")])
    data = client.get("/api/digest/weekly", headers=auth).json()
    assert data["window"] == "latest"
    assert data["total"] == 1


def test_analytics_actions_reading_topics(api, auth):
    client, store = api
    store.upsert_papers(TREND_PAPERS)
    for pid in ("t1", "t2"):
        assert client.post("/api/interactions", json={"action": "like", "paper_id": pid},
                           headers=auth).status_code == 201
    assert client.post("/api/reading", json={"paper_id": "t3"},
                       headers=auth).status_code == 201
    data = client.get("/api/analytics", headers=auth).json()
    assert data["actions"].get("like") == 2
    assert data["reading"]["to-read"] == 1
    assert sum(d["count"] for d in data["activity"]) >= 2
    topics = {t["keyword"] for t in data["topics"]}
    assert "transformer" in topics
    assert data["library"]["papers"] == 6
