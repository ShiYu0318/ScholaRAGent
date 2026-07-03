"""混合檢索：BM25、RRF 融合、HybridRetriever（用 fake embedder 的向量庫）。"""
from src.rag.vector_store import VectorStore
from src.rag.retrievers import BM25Index, HybridRetriever, reciprocal_rank_fusion
from tests.conftest import make_paper


def test_bm25_exact_term_match():
    bm25 = BM25Index().fit([
        make_paper("1", "Graph neural networks for molecules"),
        make_paper("2", "Reinforcement learning for robotics"),
        make_paper("3", "Transformers scale with data"),
    ])
    results = bm25.search("graph neural networks", k=2)
    assert results[0][0]["id"] == "1"
    assert all(s > 0 for _, s in results)


def test_bm25_no_match_returns_empty():
    bm25 = BM25Index().fit([make_paper("1", "unrelated topic here")])
    assert bm25.search("quantum entanglement cryptography") == []


def test_rrf_fuses_rankings():
    # id "b" 在兩份清單都靠前 -> 融合後應第一
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["b", "c", "a"]])
    assert fused[0][0] == "b"


def test_hybrid_combines_dense_and_sparse(fake_embedder, isolated_data):
    store = VectorStore(embedder=fake_embedder)
    store.add([
        make_paper("1", "multi agent reinforcement learning"),
        make_paper("2", "diffusion models for images"),
        make_paper("3", "reinforcement learning theory"),
    ])
    hybrid = HybridRetriever(store)
    results = hybrid.retrieve("reinforcement learning", k=2)
    ids = [p["id"] for p, _ in results]
    assert "2" not in ids           # 不相關的不該進前二
    assert len(results) == 2
    assert all(isinstance(s, float) for _, s in results)


def test_hybrid_respects_where_filter(fake_embedder, isolated_data):
    store = VectorStore(embedder=fake_embedder)
    store.add([
        make_paper("1", "reinforcement learning", source="arxiv"),
        make_paper("2", "reinforcement learning news", source="news"),
    ])
    hybrid = HybridRetriever(store)
    results = hybrid.retrieve("reinforcement learning", k=5,
                              where=lambda p: p.get("source") == "arxiv")
    assert [p["id"] for p, _ in results] == ["1"]
