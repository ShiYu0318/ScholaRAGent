"""查詢路由 local/global，離線。"""
from src.graph.router import route_query


class StubLLM:
    def __init__(self, reply):
        self.reply = reply

    def _chat(self, system, user, **kwargs):
        return self.reply


class BoomLLM:
    def _chat(self, *a, **k):
        raise RuntimeError("down")


def test_llm_routes_global():
    assert route_query("q", llm=StubLLM("global")) == "global"


def test_llm_routes_local():
    assert route_query("q", llm=StubLLM("LOCAL")) == "local"


def test_heuristic_detects_global_keywords():
    assert route_query("give an overview of the whole field", llm=None) == "global"
    assert route_query("整體趨勢與研究地圖", llm=None) == "global"


def test_heuristic_defaults_to_local():
    assert route_query("what method does this paper propose", llm=None) == "local"


def test_llm_invalid_output_falls_back_to_heuristic():
    # LLM 回無效值 -> 用啟發式（此題含 landscape -> global）
    assert route_query("landscape of the field", llm=StubLLM("banana")) == "global"


def test_llm_error_falls_back_to_heuristic():
    assert route_query("specific question", llm=BoomLLM()) == "local"
