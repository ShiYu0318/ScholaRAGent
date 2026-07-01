"""多查詢檢索器：查詢轉換 + RRF 融合（stub，離線）。"""
from src.rag.query_transform import QueryTransformer
from src.rag.retrievers.multi_query import MultiQueryRetriever


class StubLLM:
    def __init__(self, reply):
        self.reply = reply

    def _chat(self, system, user, **kwargs):
        return self.reply


def _paper(pid):
    return {"id": pid, "title": pid, "abstract": ""}


class StubRetriever:
    """依查詢字串回傳不同排序，模擬多版本檢索。"""

    def __init__(self, per_query):
        self.per_query = per_query
        self.seen = []

    def retrieve(self, query, k=4):
        self.seen.append(query)
        ids = self.per_query.get(query, [])
        return [(_paper(pid), 1.0) for pid in ids][:k]


def test_multi_query_fuses_across_variants():
    # 原查詢與兩個改寫版本各自命中不同論文
    llm = StubLLM("robot RL\nRL control")
    qt = QueryTransformer(llm)
    base = StubRetriever(
        {
            "reinforcement learning robotics": ["a", "b"],
            "robot RL": ["b", "c"],
            "RL control": ["c", "d"],
        }
    )
    mqr = MultiQueryRetriever(qt, base.retrieve)
    out = mqr.retrieve("reinforcement learning robotics", k=4, n_variants=2)
    ids = [p["id"] for p, _ in out]

    # 三個版本都被檢索
    assert base.seen == ["reinforcement learning robotics", "robot RL", "RL control"]
    # 涵蓋所有出現過的論文，且無重複
    assert set(ids) == {"a", "b", "c", "d"}
    assert len(ids) == len(set(ids))
    # 在多個版本重複命中的 b、c 應排在前面
    assert set(ids[:2]) == {"b", "c"}


def test_search_returns_plain_papers():
    qt = QueryTransformer(StubLLM(""))  # 無改寫 → 只有原查詢
    base = StubRetriever({"q": ["x", "y"]})
    mqr = MultiQueryRetriever(qt, base.retrieve)
    assert mqr.search("q", k=2) == [_paper("x"), _paper("y")]
