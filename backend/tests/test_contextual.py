"""Contextual chunk embedding，離線 stub LLM。"""
from src.rag.contextual import contextualize_chunk, contextualize_all


class StubLLM:
    def __init__(self, reply):
        self.reply = reply

    def _chat(self, system, user, **kwargs):
        return self.reply


class BoomLLM:
    def _chat(self, *a, **k):
        raise RuntimeError("down")


def test_contextualize_prepends_llm_context():
    out = contextualize_chunk("full document text", "the chunk body",
                              StubLLM("關於注意力機制的段落"))
    assert out == "關於注意力機制的段落\n\nthe chunk body"


def test_contextualize_falls_back_to_raw_on_error():
    assert contextualize_chunk("doc", "raw chunk", BoomLLM()) == "raw chunk"


def test_contextualize_falls_back_on_empty_context():
    assert contextualize_chunk("doc", "raw chunk", StubLLM("   ")) == "raw chunk"


def test_contextualize_all_maps_each_chunk():
    out = contextualize_all("doc", ["a", "b"], StubLLM("CTX"))
    assert out == ["CTX\n\na", "CTX\n\nb"]
