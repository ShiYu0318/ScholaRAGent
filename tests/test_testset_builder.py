"""Eval testset builder，離線 stub。"""
from src.rag.testset_builder import build_testset, validate_testset


def _p(pid, title):
    return {"id": pid, "title": title, "abstract": f"abstract of {title}"}


class StubLLM:
    def __init__(self, reply):
        self.reply = reply

    def _chat(self, system, user, **kwargs):
        return self.reply


class BoomLLM:
    def _chat(self, *a, **k):
        raise RuntimeError("down")


def test_builds_one_question_per_paper():
    ts = build_testset([_p("1", "A"), _p("2", "B")], StubLLM("What is the method?"))
    assert len(ts) == 2
    assert ts[0]["relevant"] == ["1"]
    assert ts[0]["query"] == "What is the method?"


def test_multiple_questions_per_paper():
    ts = build_testset([_p("1", "A")], StubLLM("Q1?\nQ2?\nQ3?"), per_paper=2)
    assert [t["query"] for t in ts] == ["Q1?", "Q2?"]


def test_llm_error_skips_paper_gracefully():
    assert build_testset([_p("1", "A")], BoomLLM()) == []


def test_validate_filters_malformed():
    raw = [
        {"query": "ok?", "relevant": ["1"]},
        {"query": "", "relevant": ["1"]},       # 空問題
        {"query": "no rel?", "relevant": []},   # 無相關文件
    ]
    assert validate_testset(raw) == [{"query": "ok?", "relevant": ["1"]}]
