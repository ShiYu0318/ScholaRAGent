"""學習路徑與技能端點：離線（stub LLM 與 LLM 失敗退回檢索式皆測）。"""
import pytest
from fastapi.testclient import TestClient

from src import store as store_module
from src.api.services import product as product_module
from src.api.services.product import ProductService
from src.store.sqlite_faiss import SqliteFaissStore


class StubLLM:
    def _chat(self, system, user, **kwargs):
        return '["讀基礎教材", "跑通範例", "重現論文", "做小專案"]'


class BrokenLLM:
    def _chat(self, system, user, **kwargs):
        raise RuntimeError("no key")


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
                        json={"email": "lp@b.c", "password": "password123"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_path_from_llm(api, auth):
    client, _ = api
    resp = client.post("/api/learning-paths",
                       json={"topic": "graph rag", "steps": 4}, headers=auth)
    assert resp.status_code == 201
    path = resp.json()
    assert path["topic"] == "graph rag"
    assert [it["title"] for it in path["items"]] == [
        "讀基礎教材", "跑通範例", "重現論文", "做小專案"]
    assert all(it["done"] is False for it in path["items"])


def test_create_path_falls_back_without_llm(api, auth):
    client, store = api
    store.upsert_papers([
        {"id": "g1", "title": "GraphRAG Survey", "abstract": "graph retrieval",
         "authors": "", "link": "http://x/g1", "published": "2026-06-01",
         "source": "arxiv"},
    ])
    prev = product_module.set_product_service(ProductService(store, llm=BrokenLLM()))
    try:
        path = client.post("/api/learning-paths",
                           json={"topic": "graphrag", "steps": 4},
                           headers=auth).json()
        titles = [it["title"] for it in path["items"]]
        assert titles[0].startswith("綜覽 graphrag")
        assert any("GraphRAG Survey" in t for t in titles)
    finally:
        product_module.set_product_service(prev)


def test_update_progress_and_delete(api, auth):
    client, _ = api
    path = client.post("/api/learning-paths",
                       json={"topic": "rag", "steps": 4}, headers=auth).json()
    pid = path["id"]
    items = path["items"]
    items[0]["done"] = True
    updated = client.patch(f"/api/learning-paths/{pid}",
                           json={"items": items, "progress": {"done": 1, "total": 4}},
                           headers=auth).json()
    assert updated["items"][0]["done"] is True
    assert updated["progress"] == {"done": 1, "total": 4}

    listed = client.get("/api/learning-paths", headers=auth).json()["items"]
    assert len(listed) == 1

    assert client.delete(f"/api/learning-paths/{pid}", headers=auth).status_code == 204
    assert client.patch(f"/api/learning-paths/{pid}", json={"topic": "x"},
                        headers=auth).status_code == 404


def test_skills_put_and_list(api, auth):
    client, _ = api
    assert client.put("/api/skills", json={"skill": "RAG", "level": 40},
                      headers=auth).status_code == 200
    client.put("/api/skills", json={"skill": "RAG", "level": 70}, headers=auth)
    client.put("/api/skills", json={"skill": "GraphRAG", "level": 20}, headers=auth)
    items = client.get("/api/skills", headers=auth).json()["items"]
    by_name = {s["skill"]: s["level"] for s in items}
    assert by_name == {"RAG": 70, "GraphRAG": 20}
    assert client.put("/api/skills", json={"skill": "RAG", "level": 101},
                      headers=auth).status_code == 422
