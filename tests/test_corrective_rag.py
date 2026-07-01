"""Corrective RAG，離線 stub。"""
from src.agent.corrective_rag import corrective_retrieve


def _p(pid):
    return {"id": pid, "title": pid, "abstract": ""}


def test_confident_retrieval_skips_correction():
    primary = [(_p("a"), 0.9), (_p("b"), 0.5)]
    called = {"n": 0}

    def fallback(q):
        called["n"] += 1
        return [_p("z")]

    res, corrected = corrective_retrieve("q", primary, fallback, min_score=0.3, k=4)
    assert corrected is False
    assert called["n"] == 0                       # 信心足夠不觸發外部搜尋
    assert [p["id"] for p, _ in res] == ["a", "b"]


def test_low_confidence_triggers_fallback():
    primary = [(_p("a"), 0.1)]
    res, corrected = corrective_retrieve("q", primary, lambda q: [_p("b")], min_score=0.3)
    assert corrected is True
    ids = [p["id"] for p, _ in res]
    assert "b" in ids and "a" in ids              # 融合本地與外部


def test_empty_primary_triggers_fallback():
    res, corrected = corrective_retrieve("q", [], lambda q: [_p("b")], min_score=0.3)
    assert corrected is True
    assert [p["id"] for p, _ in res] == ["b"]


def test_fallback_results_are_deduped():
    primary = [(_p("a"), 0.05)]
    res, corrected = corrective_retrieve("q", primary, lambda q: [_p("a"), _p("b")], min_score=0.3)
    ids = [p["id"] for p, _ in res]
    assert ids.count("a") == 1
