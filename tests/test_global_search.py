"""全域搜尋 map-reduce，離線 stub。"""
from src.graph.global_search import global_search


class SeqLLM:
    """每次呼叫回傳 r1, r2, ... 並記錄 user，方便驗證 map/reduce 次序。"""
    def __init__(self):
        self.calls = []

    def _chat(self, system, user, **kwargs):
        self.calls.append(user)
        return f"r{len(self.calls)}"


def _comms():
    return [{"nodes": ["a"], "summary": "社群一：關於檢索"},
            {"nodes": ["b"], "summary": "社群二：關於推理"}]


def test_maps_each_community_then_reduces():
    llm = SeqLLM()
    out = global_search("整體在研究什麼", _comms(), llm)
    assert len(llm.calls) == 3            # 2 個 map + 1 個 reduce
    assert out == "r3"                    # 最後一次（reduce）為最終答案
    # 兩個社群摘要都進了 map 的 prompt
    assert any("社群一" in c for c in llm.calls[:2])
    assert any("社群二" in c for c in llm.calls[:2])


def test_reduce_prompt_contains_partials():
    llm = SeqLLM()
    global_search("q", _comms(), llm)
    assert "r1" in llm.calls[-1] and "r2" in llm.calls[-1]   # reduce 吃到各 map 結果


def test_empty_communities_returns_message():
    out = global_search("q", [], SeqLLM())
    assert "社群" in out and out != "r1"


def test_respects_max_communities():
    llm = SeqLLM()
    global_search("q", _comms() * 5, llm, max_communities=3)
    assert len(llm.calls) == 3 + 1        # 3 個 map + 1 reduce
