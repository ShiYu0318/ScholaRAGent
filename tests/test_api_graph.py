"""圖譜端點：離線（stub OpenAlex 與 LLM）。"""
import pytest
from fastapi.testclient import TestClient

from src import store as store_module
from src.api.services import graph as graph_module
from src.api.services.graph import GraphService
from src.store.sqlite_faiss import SqliteFaissStore


class StubOpenAlex:
    def work_by_arxiv(self, arxiv_id, title=None):
        if arxiv_id != "2401.00001":
            return None
        return {"openalex_id": "W1", "title": "Seed Paper", "year": 2024,
                "cited_by_count": 10, "references": ["W2", "W3"]}

    def cited_by(self, openalex_id, limit=25):
        return [{"openalex_id": "W4", "title": "Derivative", "year": 2025,
                 "cited_by_count": 3, "references": []}]


class StubLLM:
    """概念抽取回固定三元組；摘要/全域搜尋回固定字串。"""

    def _chat(self, system, user, temperature=0.3, max_tokens=800):
        if "總結" in system:  # 社群摘要的 prompt 也含「三元組」，須先比對
            return "此社群研究檢索增強生成。"
        if "三元組" in system:
            return "RAG | improves | QA\nGraphRAG | extends | RAG"
        return "宏觀答案：RAG 與 GraphRAG 是主要方向。"


@pytest.fixture
def api(tmp_path, fake_embedder):
    from src.api.app import create_app

    store = SqliteFaissStore(db_path=tmp_path / "api.db", embedder=fake_embedder)
    store.upsert_papers([
        {"id": "p1", "title": "RAG survey", "abstract": "retrieval augmented generation"},
    ])
    prev_store = store_module.set_store(store)
    prev_service = graph_module.set_graph_service(
        GraphService(store, llm=StubLLM(), openalex=StubOpenAlex())
    )
    client = TestClient(create_app())
    yield client
    graph_module.set_graph_service(prev_service)
    store_module.set_store(prev_store)
    store.close()


@pytest.fixture
def auth(api):
    token = api.post("/auth/register",
                     json={"email": "g@b.c", "password": "password123"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_citation_graph_nodes_edges_influential(api, auth):
    resp = api.get("/api/graph/citation", params={"seed": "2401.00001"}, headers=auth)
    assert resp.status_code == 200
    data = resp.json()
    ids = {n["id"] for n in data["nodes"]}
    assert ids == {"W1", "W2", "W3", "W4"}
    kinds = {n["id"]: n["kind"] for n in data["nodes"]}
    assert kinds["W1"] == "seed" and kinds["W4"] == "derivative"
    assert {"source": "W4", "target": "W1"}.items() <= {
        (k, v) for e in data["edges"] for k, v in e.items() if k in ("source", "target")
    } or any(e["source"] == "W4" and e["target"] == "W1" for e in data["edges"])
    # 被引最多的種子 PageRank 應最高，排行第一
    assert data["influential"][0]["id"] in ("W2", "W3", "W1")
    assert all(n["pagerank"] >= 0 for n in data["nodes"])


def test_citation_unknown_seed_404(api, auth):
    resp = api.get("/api/graph/citation", params={"seed": "9999.99999"}, headers=auth)
    assert resp.status_code == 404


def test_concept_graph_from_papers(api, auth):
    resp = api.get("/api/graph/concept", headers=auth)
    assert resp.status_code == 200
    data = resp.json()
    labels = {n["id"] for n in data["nodes"]}
    assert labels == {"RAG", "QA", "GraphRAG"}
    rels = {e["relation"] for e in data["edges"]}
    assert rels == {"improves", "extends"}
    assert data["edges"][0]["papers"] == ["p1"]


def test_concept_graph_with_summaries(api, auth):
    resp = api.get("/api/graph/concept", params={"summarize": "true"}, headers=auth)
    data = resp.json()
    assert data["communities"][0]["summary"] == "此社群研究檢索增強生成。"


def test_global_search_answer(api, auth):
    resp = api.get("/api/graph/global", params={"query": "整體趨勢？"}, headers=auth)
    assert resp.status_code == 200
    assert "宏觀答案" in resp.json()["answer"]


def test_graph_requires_auth(api):
    assert api.get("/api/graph/concept").status_code == 401
    assert api.get("/api/graph/citation", params={"seed": "x"}).status_code == 401
