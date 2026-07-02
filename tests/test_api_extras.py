"""補充端點（sources/memory/eval/agent）：離線。"""
import pytest
from fastapi.testclient import TestClient

from src import store as store_module
from src.api.routers import extras as extras_module
from src.memory.memory_store import MemoryStore
from src.store.sqlite_faiss import SqliteFaissStore


class FakeAgent:
    def run(self, message, max_steps=5):
        return f"代理回覆：{message}"


@pytest.fixture
def api(tmp_path, fake_embedder, isolated_data):
    from src.api.app import create_app

    store = SqliteFaissStore(db_path=tmp_path / "api.db", embedder=fake_embedder)
    prev_store = store_module.set_store(store)
    prev_memory = extras_module.set_memory(MemoryStore(path=tmp_path / "memory.json"))
    prev_agent = extras_module.set_tool_agent(FakeAgent())
    client = TestClient(create_app())
    yield client, store
    extras_module.set_tool_agent(prev_agent)
    extras_module.set_memory(prev_memory)
    store_module.set_store(prev_store)
    store.close()


@pytest.fixture
def auth(api):
    client, _ = api
    token = client.post("/auth/register",
                        json={"email": "x@b.c", "password": "password123"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_sources_reflect_config_and_feeds(api, auth):
    client, _ = api
    items = {s["name"]: s for s in client.get("/api/sources", headers=auth).json()["items"]}
    assert items["arxiv"]["configured"] is True
    assert items["rss"]["configured"] is False
    client.post("/api/feeds", json={"url": "http://example.com/rss"}, headers=auth)
    items = {s["name"]: s for s in client.get("/api/sources", headers=auth).json()["items"]}
    assert items["rss"]["configured"] is True and items["rss"]["detail"] == "1 feeds"


def test_memory_add_and_filter(api, auth):
    client, _ = api
    assert client.post("/api/memory", json={"content": "偏好 GraphRAG 主題",
                                            "kind": "preference"},
                       headers=auth).status_code == 201
    client.post("/api/memory", json={"content": "問過 RAG 評估"}, headers=auth)

    items = client.get("/api/memory", headers=auth).json()["items"]
    assert len(items) == 2
    prefs = client.get("/api/memory", params={"kind": "preference"},
                       headers=auth).json()["items"]
    assert len(prefs) == 1 and "GraphRAG" in prefs[0]["content"]
    hits = client.get("/api/memory", params={"contains": "評估"},
                      headers=auth).json()["items"]
    assert len(hits) == 1


def test_memory_is_per_user(api, auth):
    client, _ = api
    client.post("/api/memory", json={"content": "mine"}, headers=auth)
    other = client.post("/auth/register",
                        json={"email": "x2@b.c", "password": "password123"}).json()["token"]
    assert client.get("/api/memory",
                      headers={"Authorization": f"Bearer {other}"}).json()["items"] == []


def test_eval_metrics(api, auth):
    client, _ = api
    body = {"retrieved_ids": ["a", "b", "c"], "relevant_ids": ["b"], "k": 2}
    data = client.post("/api/eval", json=body, headers=auth).json()
    assert data["precision_at_k"] == 0.5
    assert data["recall"] == 1.0
    assert data["mrr"] == 0.5
    assert "faithfulness" not in data

    body.update({"answer": "graph attention networks", "contexts": ["graph attention"]})
    data = client.post("/api/eval", json=body, headers=auth).json()
    assert 0.0 <= data["faithfulness"] <= 1.0


def test_agent_with_stub_and_degradation(api, auth, monkeypatch):
    client, _ = api
    data = client.post("/api/agent", json={"message": "找 RAG 論文"},
                       headers=auth).json()
    assert data["answer"] == "代理回覆：找 RAG 論文"

    # 未設 GROQ_API_KEY 且無注入代理時降級 503
    from src import config
    monkeypatch.setattr(config, "GROQ_API_KEY", "")
    prev = extras_module.set_tool_agent(None)
    try:
        resp = client.post("/api/agent", json={"message": "hi"}, headers=auth)
        assert resp.status_code == 503
    finally:
        extras_module.set_tool_agent(prev)
