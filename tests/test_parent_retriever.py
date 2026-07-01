"""父文件回溯檢索（v2/A4）：small-to-big，離線 FakeEmbedder。"""
from src.rag.retrievers.parent import ParentDocumentRetriever


def _paper(pid, title, abstract):
    return {"id": pid, "title": title, "abstract": abstract}


def test_retrieve_returns_parent_of_best_child_chunk(fake_embedder):
    r = ParentDocumentRetriever(embedder=fake_embedder, child_size=60, child_overlap=0)
    r.index([
        _paper("1", "A", "Cats are mammals. Dogs bark loudly at night."),
        _paper("2", "B", "Graph networks model relations. Transformers use attention."),
    ])
    out = r.retrieve("transformers attention", k=1)
    assert [p["id"] for p, _ in out] == ["2"]


def test_retrieve_dedupes_one_entry_per_parent(fake_embedder):
    r = ParentDocumentRetriever(embedder=fake_embedder, child_size=50, child_overlap=0)
    r.index([
        _paper("1", "A", "Attention is powerful. Attention helps a lot. Attention wins."),
        _paper("2", "B", "Cats are mammals. Dogs bark loudly."),
    ])
    out = r.retrieve("attention", k=5)
    ids = [p["id"] for p, _ in out]
    assert ids.count("1") == 1          # 多個子片段命中，父文件仍只出現一次


def test_retrieve_empty_index_returns_empty(fake_embedder):
    r = ParentDocumentRetriever(embedder=fake_embedder)
    assert r.retrieve("anything", k=3) == []
