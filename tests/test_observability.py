"""查詢可觀測性日誌（v2/E2）。"""
from src.utils.query_log import log_query, read_queries, summarize


def test_log_and_read_roundtrip(tmp_path):
    path = tmp_path / "queries.jsonl"
    log_query({"query": "a", "hits": 3, "latency_ms": 12}, path=path)
    log_query({"query": "b", "hits": 0, "latency_ms": 5}, path=path)
    rows = read_queries(path)
    assert [r["query"] for r in rows] == ["a", "b"]
    assert rows[0]["hits"] == 3


def test_summarize_counts(tmp_path):
    path = tmp_path / "q.jsonl"
    for q in ["a", "a", "b"]:
        log_query({"query": q, "hits": 1, "latency_ms": 10}, path=path)
    s = summarize(path)
    assert s["total"] == 3
    assert s["zero_hit"] == 0
    assert s["avg_latency_ms"] == 10


def test_read_missing_file_returns_empty(tmp_path):
    assert read_queries(tmp_path / "nope.jsonl") == []
