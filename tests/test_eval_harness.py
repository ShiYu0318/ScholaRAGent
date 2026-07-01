"""檢索評估 harness。"""
from src.rag.eval_harness import evaluate_retrieval


def _make_retrieve(data):
    def retrieve(query, k=4):
        return [({"id": i}, 1.0) for i in data.get(query, [])][:k]
    return retrieve


def test_aggregates_metrics_across_dataset():
    retrieve = _make_retrieve({"q1": ["a", "b"], "q2": ["x", "c"]})
    dataset = [{"query": "q1", "relevant": ["a"]},
               {"query": "q2", "relevant": ["c"]}]
    res = evaluate_retrieval(retrieve, dataset, k=2)
    # q1: 命中在第1名 -> RR 1.0；q2: c 在第2名 -> RR 0.5
    assert res["mrr"] == 0.75
    assert res["recall"] == 1.0
    assert res["precision@k"] == 0.5      # 每題 2 取 1 相關
    assert res["n"] == 2


def test_empty_dataset_returns_zeros():
    res = evaluate_retrieval(_make_retrieve({}), [], k=3)
    assert res["mrr"] == 0.0 and res["n"] == 0
