"""引用準確度指標。"""
from src.rag.evaluation import citation_accuracy


def test_valid_and_grounded_citation_scores_one():
    chunks = [{"id": "c1", "text": "attention improves translation quality"}]
    answer = "Attention improves translation quality [REF:c1]."
    acc = citation_accuracy(answer, chunks)
    assert acc["valid_ratio"] == 1.0
    assert acc["grounded_ratio"] == 1.0
    assert acc["score"] == 1.0


def test_invalid_ref_scores_zero():
    chunks = [{"id": "c1", "text": "foo"}]
    acc = citation_accuracy("claim [REF:zzz].", chunks)
    assert acc["valid_ratio"] == 0.0
    assert acc["score"] == 0.0


def test_valid_but_ungrounded_citation():
    chunks = [{"id": "c1", "text": "quantum hardware qubits"}]
    answer = "Graph neural networks are powerful [REF:c1]."
    acc = citation_accuracy(answer, chunks)
    assert acc["valid_ratio"] == 1.0          # id 存在
    assert acc["grounded_ratio"] == 0.0       # 但與答案內容無關
    assert acc["score"] == 0.0


def test_no_citations_scores_zero():
    acc = citation_accuracy("no citations here", [{"id": "c1", "text": "x"}])
    assert acc["score"] == 0.0 and acc["n_refs"] == 0
