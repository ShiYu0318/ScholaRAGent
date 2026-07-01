"""查詢轉換：HyDE / multi-query / decompose（stub LLM，離線）。"""
from src.rag.query_transform import QueryTransformer, _parse_lines


class StubLLM:
    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    def _chat(self, system, user, **kwargs):
        self.calls.append({"system": system, "user": user})
        return self.reply


class BoomLLM:
    def _chat(self, *a, **k):
        raise RuntimeError("api down")


def test_parse_lines_strips_numbering():
    text = "1. first\n2) second\n- third\n\n   \n* fourth"
    assert _parse_lines(text) == ["first", "second", "third", "fourth"]
    assert _parse_lines(text, limit=2) == ["first", "second"]


def test_hyde_returns_passage():
    qt = QueryTransformer(StubLLM("A hypothetical abstract about agents."))
    assert qt.hyde("what is agentic rag?") == "A hypothetical abstract about agents."


def test_hyde_falls_back_on_error():
    qt = QueryTransformer(BoomLLM())
    assert qt.hyde("my query") == "my query"


def test_multi_query_includes_original_and_variants():
    qt = QueryTransformer(StubLLM("RL for robotics\nrobot reinforcement learning\nRL control"))
    out = qt.multi_query("reinforcement learning robotics", n=3)
    assert out[0] == "reinforcement learning robotics"   # 原查詢在首位
    assert "RL for robotics" in out
    assert len(out) <= 4


def test_multi_query_dedupes_original():
    qt = QueryTransformer(StubLLM("my query\nanother phrasing"))
    out = qt.multi_query("my query", n=3)
    assert out.count("my query") == 1


def test_decompose_returns_subquestions():
    qt = QueryTransformer(StubLLM("What is X?\nHow does X compare to Y?"))
    subs = qt.decompose("Compare X and Y")
    assert subs == ["What is X?", "How does X compare to Y?"]


def test_decompose_falls_back_on_error():
    qt = QueryTransformer(BoomLLM())
    assert qt.decompose("q") == ["q"]
