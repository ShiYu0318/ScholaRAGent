"""Adaptive-RAG（v2/B6）：依問題複雜度選檢索策略，離線。"""
from src.agent.adaptive_rag import classify_complexity, adaptive_retrieve


class StubLLM:
    def __init__(self, reply):
        self.reply = reply

    def _chat(self, system, user, **kwargs):
        return self.reply


class BoomLLM:
    def _chat(self, *a, **k):
        raise RuntimeError("down")


# --- 複雜度分類 ---

def test_llm_classifies_complexity():
    assert classify_complexity("q", llm=StubLLM("complex")) == "complex"
    assert classify_complexity("q", llm=StubLLM("SIMPLE")) == "simple"
    assert classify_complexity("q", llm=StubLLM("none")) == "none"


def test_heuristic_none_for_greeting():
    assert classify_complexity("hello there", llm=None) == "none"


def test_heuristic_complex_for_multi_part():
    assert classify_complexity("compare A and B and explain how they differ", llm=None) == "complex"


def test_heuristic_default_simple():
    assert classify_complexity("what is retrieval augmented generation", llm=None) == "simple"


def test_llm_error_falls_back_to_heuristic():
    assert classify_complexity("hi", llm=BoomLLM()) == "none"


# --- 依複雜度分派 ---

def test_none_skips_retrieval():
    out = adaptive_retrieve("hello", simple_retrieve=lambda q: [{"id": "x"}],
                            multi_retrieve=lambda q: [{"id": "y"}], llm=StubLLM("none"))
    assert out == []


def test_simple_uses_single_shot():
    out = adaptive_retrieve("what is X", simple_retrieve=lambda q: [{"id": "s"}],
                            multi_retrieve=lambda q: [{"id": "m"}], llm=StubLLM("simple"))
    assert [p["id"] for p in out] == ["s"]


def test_complex_uses_multi_step():
    out = adaptive_retrieve("compare and contrast", simple_retrieve=lambda q: [{"id": "s"}],
                            multi_retrieve=lambda q: [{"id": "m"}], llm=StubLLM("complex"))
    assert [p["id"] for p in out] == ["m"]
