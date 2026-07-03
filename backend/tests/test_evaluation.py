"""RAG 離線評估指標。"""
from src.rag.evaluation import (
    precision_at_k, recall, reciprocal_rank, faithfulness,
)


def test_precision_at_k():
    assert precision_at_k(["a", "b", "c", "d"], {"a", "c"}, k=4) == 0.5


def test_precision_at_k_truncates_to_k():
    assert precision_at_k(["a", "b", "c"], {"a"}, k=2) == 0.5   # 前2=a,b -> 1/2


def test_recall():
    assert recall(["a", "b"], {"a", "c"}) == 0.5


def test_reciprocal_rank_uses_first_relevant():
    assert reciprocal_rank(["x", "a", "b"], {"a"}) == 0.5       # 命中在第2名


def test_reciprocal_rank_none_relevant():
    assert reciprocal_rank(["x", "y"], {"a"}) == 0.0


def test_faithfulness_fully_supported():
    assert faithfulness("graph neural networks",
                        ["graph neural networks model relations"]) == 1.0


def test_faithfulness_partial():
    assert faithfulness("graph quantum", ["graph neural networks"]) == 0.5


def test_metrics_empty_safe():
    assert precision_at_k([], {"a"}, k=3) == 0.0
    assert recall(["a"], set()) == 0.0
    assert faithfulness("", ["x"]) == 0.0
