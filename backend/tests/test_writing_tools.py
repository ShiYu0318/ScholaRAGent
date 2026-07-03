"""寫作助理強化，離線 stub。"""
from src.tools.writing_tools import polish_text, extract_contributions, review_checklist


class StubLLM:
    def __init__(self, reply="OUT"):
        self.reply = reply
        self.seen = []

    def _chat(self, system, user, **kwargs):
        self.seen.append((system, user))
        return self.reply


def test_polish_passes_text_to_llm():
    llm = StubLLM("polished")
    assert polish_text("bad grammer here", llm) == "polished"
    assert "bad grammer here" in llm.seen[0][1]


def test_extract_contributions_returns_llm_output():
    assert extract_contributions("our method ...", StubLLM("- c1")) == "- c1"


def test_review_checklist_uses_topic():
    llm = StubLLM("checklist")
    review_checklist("multi-agent RL", llm)
    assert "multi-agent RL" in llm.seen[0][1]
