"""研究/寫作端點：離線（stub 服務）。"""
import json

import pytest
from fastapi.testclient import TestClient

from src import store as store_module
from src.api.services import research as research_module
from src.store.sqlite_faiss import SqliteFaissStore


class StubResearchService:
    def stream_deepresearch(self, topic, max_subs=4, k=4):
        yield {"type": "decompose", "questions": ["子題一", "子題二"]}
        yield {"type": "section", "question": "子題一", "content": "摘要一", "papers": ["p1"]}
        yield {"type": "section", "question": "子題二", "content": "摘要二", "papers": []}
        yield {"type": "synthesis", "content": "綜合結論"}
        yield {"type": "citations", "citations": [{"id": "p1", "title": "T1"}]}
        yield {"type": "done"}

    def litreview(self, topic, k=8):
        return {"content": f"# 綜述：{topic}", "papers": ["p1"]}

    def compare(self, topic=None, paper_ids=None, k=6):
        return {"content": "| 論文 | 方法 |", "papers": paper_ids or ["p1"]}

    def report(self, topic, k=8):
        return {"content": f"## 主題概述 {topic}", "papers": ["p1"]}

    def bibtex(self, topic=None, paper_ids=None, k=8):
        return {"content": "@article{x2026,}", "papers": ["p1"]}

    def explain(self, paper_id):
        if paper_id != "p1":
            return None
        return {"content": "白話解讀", "papers": ["p1"]}

    def write(self, tool, text="", topic=""):
        return f"{tool}:{(text or topic)[:10]}"


@pytest.fixture
def api(tmp_path, fake_embedder):
    from src.api.app import create_app

    store = SqliteFaissStore(db_path=tmp_path / "api.db", embedder=fake_embedder)
    prev_store = store_module.set_store(store)
    prev_service = research_module.set_research_service(StubResearchService())
    client = TestClient(create_app())
    yield client
    research_module.set_research_service(prev_service)
    store_module.set_store(prev_store)
    store.close()


@pytest.fixture
def auth(api):
    token = api.post("/auth/register",
                     json={"email": "r@b.c", "password": "password123"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_deepresearch_streams_stages(api, auth):
    resp = api.post("/api/deepresearch", json={"topic": "GraphRAG"}, headers=auth)
    assert resp.status_code == 200
    events = [json.loads(l[len("data: "):]) for l in resp.text.splitlines()
              if l.startswith("data: ")]
    types = [e["type"] for e in events]
    assert types == ["decompose", "section", "section", "synthesis", "citations", "done"]
    assert events[0]["questions"] == ["子題一", "子題二"]


def test_litreview_report_compare_bibtex(api, auth):
    assert "綜述" in api.post("/api/litreview", json={"topic": "RAG"},
                              headers=auth).json()["content"]
    assert "主題概述" in api.post("/api/report", json={"topic": "RAG"},
                                  headers=auth).json()["content"]
    assert "| 論文 |" in api.post("/api/compare", json={"paper_ids": ["p1", "p2"]},
                                  headers=auth).json()["content"]
    assert "@article" in api.post("/api/bibtex", json={"topic": "RAG"},
                                  headers=auth).json()["content"]


def test_compare_requires_topic_or_ids(api, auth):
    assert api.post("/api/compare", json={}, headers=auth).status_code == 422


def test_explain_found_and_missing(api, auth):
    assert api.post("/api/explain", json={"paper_id": "p1"},
                    headers=auth).json()["content"] == "白話解讀"
    assert api.post("/api/explain", json={"paper_id": "nope"},
                    headers=auth).status_code == 404
    assert api.post("/api/explain", json={}, headers=auth).status_code == 422


def test_write_tools(api, auth):
    for tool in ("polish", "contributions", "checklist", "latex", "slides", "review"):
        resp = api.post(f"/api/write/{tool}", json={"text": "一段文字"}, headers=auth)
        assert resp.status_code == 200
        assert resp.json()["content"].startswith(tool)
    assert api.post("/api/write/unknown", json={"text": "x"}, headers=auth).status_code == 404
    assert api.post("/api/write/polish", json={}, headers=auth).status_code == 422


def test_research_requires_auth(api):
    assert api.post("/api/litreview", json={"topic": "x"}).status_code == 401
    assert api.post("/api/deepresearch", json={"topic": "x"}).status_code == 401
