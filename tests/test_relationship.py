"""論文關係分析，離線 stub。"""
from src.graph.relationship import analyze_relationship, KNOWN_RELATIONS


def _p(title):
    return {"title": title, "abstract": f"abstract of {title}"}


class StubLLM:
    def __init__(self, reply):
        self.reply = reply
        self.seen = []

    def _chat(self, system, user, **kwargs):
        self.seen.append(user)
        return self.reply


class BoomLLM:
    def _chat(self, *a, **k):
        raise RuntimeError("down")


def test_parses_known_relation_and_explanation():
    r = analyze_relationship(_p("A"), _p("B"), StubLLM("extends: B improves A's attention."))
    assert r["relation"] == "extends"
    assert "improves" in r["explanation"]
    assert r["relation"] in KNOWN_RELATIONS


def test_both_titles_in_prompt():
    llm = StubLLM("uses: -")
    analyze_relationship(_p("Alpha"), _p("Beta"), llm)
    assert "Alpha" in llm.seen[0] and "Beta" in llm.seen[0]


def test_unknown_label_becomes_related():
    r = analyze_relationship(_p("A"), _p("B"), StubLLM("frobnicates: weird output"))
    assert r["relation"] == "related"


def test_no_colon_is_unknown():
    r = analyze_relationship(_p("A"), _p("B"), StubLLM("no structure here"))
    assert r["relation"] == "unknown"


def test_error_returns_unknown():
    r = analyze_relationship(_p("A"), _p("B"), BoomLLM())
    assert r["relation"] == "unknown" and r["explanation"] == ""
