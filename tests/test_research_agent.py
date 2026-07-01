"""檢索式 ReAct agent（v2/B1）：多輪檢索，離線 stub。"""
from src.agent.research_agent import ResearchAgent


def _p(pid):
    return {"id": pid, "title": pid, "abstract": ""}


class StubRetriever:
    def __init__(self, per_query):
        self.per_query = per_query
        self.queries = []

    def retrieve(self, query, k=4):
        self.queries.append(query)
        return [(_p(pid), 1.0) for pid in self.per_query.get(query, [])]


class SeqLLM:
    """依序回傳預設回覆（模擬決定下一個查詢 / DONE）。"""
    def __init__(self, replies):
        self.replies = list(replies)

    def _chat(self, system, user, **kwargs):
        return self.replies.pop(0) if self.replies else "DONE"


def test_gather_accumulates_papers_across_rounds():
    retr = StubRetriever({"start": ["a"], "follow": ["b"]})
    agent = ResearchAgent(SeqLLM(["follow", "DONE"]), retr.retrieve)
    papers = agent.gather("start", max_rounds=3)
    assert [p["id"] for p in papers] == ["a", "b"]
    assert retr.queries == ["start", "follow"]


def test_gather_stops_when_llm_says_done():
    retr = StubRetriever({"start": ["a"], "follow": ["b"]})
    agent = ResearchAgent(SeqLLM(["DONE"]), retr.retrieve)
    papers = agent.gather("start", max_rounds=3)
    assert [p["id"] for p in papers] == ["a"]


def test_gather_dedupes_papers():
    retr = StubRetriever({"start": ["a", "b"], "follow": ["b", "c"]})
    agent = ResearchAgent(SeqLLM(["follow", "DONE"]), retr.retrieve)
    papers = agent.gather("start", max_rounds=3)
    assert [p["id"] for p in papers] == ["a", "b", "c"]


def test_gather_respects_max_rounds():
    retr = StubRetriever({"start": ["a"], "q2": ["b"], "q3": ["c"]})
    # LLM 一直想追問，但 max_rounds=2 應只跑兩輪
    agent = ResearchAgent(SeqLLM(["q2", "q3", "q4"]), retr.retrieve)
    papers = agent.gather("start", max_rounds=2)
    assert [p["id"] for p in papers] == ["a", "b"]
    assert retr.queries == ["start", "q2"]
