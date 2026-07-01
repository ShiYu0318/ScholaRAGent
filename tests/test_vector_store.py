"""VectorStore：去重、檢索、metadata 過濾、rerank、存讀往返。"""
from src.rag.vector_store import VectorStore, _lexical_overlap, _tokenize
from tests.conftest import make_paper


def _store(embedder):
    return VectorStore(embedder=embedder)


def test_add_dedup(fake_embedder, isolated_data):
    store = _store(fake_embedder)
    papers = [make_paper("1", "graph neural networks"),
              make_paper("2", "reinforcement learning")]
    added = store.add(papers)
    assert len(added) == 2
    # 重複 id 不再新增
    again = store.add([make_paper("1", "graph neural networks")])
    assert again == []
    assert len(store.papers) == 2


def test_search_returns_relevant(fake_embedder, isolated_data):
    store = _store(fake_embedder)
    store.add([
        make_paper("1", "multi agent reinforcement learning"),
        make_paper("2", "protein folding with diffusion"),
        make_paper("3", "agent planning and reasoning"),
    ])
    results = store.search("multi agent reinforcement learning", k=2)
    assert len(results) == 2
    assert results[0]["id"] == "1"  # 完全吻合應排第一


def test_search_empty_index(fake_embedder, isolated_data):
    store = _store(fake_embedder)
    assert store.search("anything") == []


def test_metadata_filter(fake_embedder, isolated_data):
    store = _store(fake_embedder)
    store.add([
        make_paper("1", "agent learning", source="arxiv"),
        make_paper("2", "agent learning news", source="hackernews"),
    ])
    results = store.search("agent learning", k=5,
                           where=lambda p: p.get("source") == "arxiv")
    assert [p["id"] for p in results] == ["1"]


def test_search_scored_sorted(fake_embedder, isolated_data):
    store = _store(fake_embedder)
    store.add([
        make_paper("1", "reinforcement learning agents"),
        make_paper("2", "computer vision segmentation"),
    ])
    scored = store.search_scored("reinforcement learning agents", k=2)
    assert scored[0][0]["id"] == "1"
    assert scored[0][1] >= scored[1][1]


def test_persistence_roundtrip(fake_embedder, isolated_data):
    store = _store(fake_embedder)
    store.add([make_paper("1", "graph neural networks"),
               make_paper("2", "language models")])
    # 重新建立一個 store，應從磁碟載回相同論文
    reloaded = VectorStore(embedder=fake_embedder)
    assert {p["id"] for p in reloaded.papers} == {"1", "2"}
    assert reloaded.index.ntotal == 2
    # 去重集合也應正確還原
    assert reloaded.add([make_paper("1", "dup")]) == []


def test_lexical_helpers():
    assert _tokenize("Multi-Agent RL!") == {"multi", "agent", "rl"}
    assert _lexical_overlap({"agent"}, "agent based model") > 0
    assert _lexical_overlap(set(), "anything") == 0.0
