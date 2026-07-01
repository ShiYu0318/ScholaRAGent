"""深度研究模式，離線 stub。"""
from src.agent.deep_research import DeepResearcher


def _p(pid):
    return {"id": pid, "title": pid, "abstract": "", "link": f"http://{pid}"}


class StubTransformer:
    def __init__(self, subs):
        self.subs = subs

    def decompose(self, topic, max_sub=4):
        return self.subs


class StubRetriever:
    def __init__(self, per_query):
        self.per_query = per_query

    def retrieve(self, query, k=4):
        return [(_p(pid), 1.0) for pid in self.per_query.get(query, [])]


class StubLLM:
    def answer(self, question, papers):
        return f"ans:{question}"

    def _chat(self, system, user, **kwargs):
        return "SYNTHESIS"


def _researcher():
    transformer = StubTransformer(["subA", "subB"])
    retr = StubRetriever({"subA": ["1"], "subB": ["1", "2"]})
    return DeepResearcher(StubLLM(), retr.retrieve, transformer)


def test_report_has_a_section_per_subquestion():
    report, _ = _researcher().run("topic")
    assert "## subA" in report and "## subB" in report
    assert "ans:subA" in report and "ans:subB" in report


def test_report_includes_synthesis_and_citations():
    report, papers = _researcher().run("topic")
    assert "SYNTHESIS" in report
    assert "來源" in report                      # 引用區塊
    assert [p["id"] for p in papers] == ["1", "2"]   # 跨小節去重


def test_topic_appears_as_title():
    report, _ = _researcher().run("multi-agent RL")
    assert "multi-agent RL" in report
