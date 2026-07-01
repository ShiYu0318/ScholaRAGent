"""語意快取 + 引用標註（v2/A5），離線。"""
from src.rag.semantic_cache import SemanticCache
from src.rag.citations import format_citations


def test_cache_returns_value_for_identical_query(fake_embedder):
    c = SemanticCache(embedder=fake_embedder, threshold=0.85)
    c.put("what is attention in transformers", "ANSWER")
    assert c.get("what is attention in transformers") == "ANSWER"


def test_cache_hit_on_highly_similar_query(fake_embedder):
    c = SemanticCache(embedder=fake_embedder, threshold=0.5)
    c.put("graph neural networks for molecules", "GNN")
    # 高詞彙重疊 → 命中
    assert c.get("graph neural networks molecules") == "GNN"


def test_cache_miss_on_dissimilar_query(fake_embedder):
    c = SemanticCache(embedder=fake_embedder, threshold=0.85)
    c.put("cats and dogs pets", "A1")
    assert c.get("quantum error correction codes") is None


def test_cache_empty_returns_none(fake_embedder):
    c = SemanticCache(embedder=fake_embedder)
    assert c.get("anything") is None


def test_format_citations_numbers_papers():
    papers = [
        {"id": "2501.1", "title": "Attention Nets", "link": "http://a"},
        {"id": "2501.2", "title": "Graph RAG", "link": "http://b"},
    ]
    out = format_citations(papers)
    assert "[1]" in out and "[2]" in out
    assert "Attention Nets" in out and "2501.2" in out
    assert "http://a" in out


def test_format_citations_empty():
    assert format_citations([]) == ""
