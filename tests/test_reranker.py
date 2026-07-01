"""BGE cross-encoder 重排序：注入 stub scorer，離線。"""
from src.rag.retrievers.reranker import CrossEncoderReranker


def _paper(pid, title, abstract=""):
    return {"id": pid, "title": title, "abstract": abstract}


class StubScorer:
    """依關鍵字回傳分數；記錄看過的 (query, doc) 配對。"""

    def __init__(self, by_kw):
        self.by_kw = by_kw
        self.pairs = None

    def __call__(self, pairs):
        self.pairs = list(pairs)
        return [next(v for kw, v in self.by_kw.items() if kw in text)
                for _q, text in self.pairs]


def test_rerank_orders_by_cross_encoder_score():
    # 先驗分數（prior）與 cross-encoder 分數刻意相反，確認由 CE 決定順序
    scorer = StubScorer({"alpha": 0.1, "bravo": 0.9, "charlie": 0.5})
    reranker = CrossEncoderReranker(scorer=scorer)
    cands = [(_paper("a", "alpha"), 0.9),
             (_paper("b", "bravo"), 0.2),
             (_paper("c", "charlie"), 0.5)]
    out = reranker.rerank("q", cands)
    assert [p["id"] for p, _ in out] == ["b", "c", "a"]
    assert out[0][1] == 0.9  # 回傳的是 CE 分數


def test_rerank_pairs_query_with_title_and_abstract():
    scorer = StubScorer({"x": 1.0})
    reranker = CrossEncoderReranker(scorer=scorer)
    reranker.rerank("my query", [(_paper("x", "Title X", "Body x here"), 0.0)])
    assert scorer.pairs == [("my query", "Title X. Body x here")]


def test_rerank_limits_to_k():
    scorer = StubScorer({"alpha": 0.1, "bravo": 0.9, "charlie": 0.5})
    reranker = CrossEncoderReranker(scorer=scorer)
    cands = [(_paper("a", "alpha"), 0), (_paper("b", "bravo"), 0), (_paper("c", "charlie"), 0)]
    out = reranker.rerank("q", cands, k=2)
    assert [p["id"] for p, _ in out] == ["b", "c"]


def test_rerank_empty_returns_empty():
    reranker = CrossEncoderReranker(scorer=StubScorer({}))
    assert reranker.rerank("q", []) == []


def test_rerank_falls_back_to_original_on_error():
    def boom(pairs):
        raise RuntimeError("model down")
    reranker = CrossEncoderReranker(scorer=boom)
    cands = [(_paper("a", "alpha"), 0.3), (_paper("b", "bravo"), 0.9)]
    out = reranker.rerank("q", cands, k=2)
    # 失敗時保留原本傳入順序（不排序、不丟例外）
    assert [p["id"] for p, _ in out] == ["a", "b"]
