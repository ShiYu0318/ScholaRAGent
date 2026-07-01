"""Self-RAG 充分性反思（v2/B2），離線 stub。"""
from src.agent.self_rag import assess_sufficiency


class StubLLM:
    def __init__(self, reply):
        self.reply = reply

    def _chat(self, system, user, **kwargs):
        return self.reply


class BoomLLM:
    def _chat(self, *a, **k):
        raise RuntimeError("down")


def test_sufficient_when_llm_says_yes():
    ok, refine = assess_sufficiency("q", ["ctx"], StubLLM("YES"))
    assert ok is True and refine is None


def test_insufficient_with_refined_query():
    ok, refine = assess_sufficiency("q", ["ctx"], StubLLM("NO: transformer memory efficiency"))
    assert ok is False
    assert refine == "transformer memory efficiency"


def test_insufficient_without_refine():
    ok, refine = assess_sufficiency("q", ["ctx"], StubLLM("NO"))
    assert ok is False and refine is None


def test_error_defaults_to_sufficient():
    # 失敗時視為足夠，避免無限重試
    ok, refine = assess_sufficiency("q", ["ctx"], BoomLLM())
    assert ok is True and refine is None
