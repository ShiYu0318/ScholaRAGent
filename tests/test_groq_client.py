"""GroqClient：prompt 組裝與無資料時的保護行為（以 stub 取代網路呼叫）。"""
from src.llm.groq_client import GroqClient
from tests.conftest import make_paper


def _client(monkeypatch, capture):
    client = GroqClient.__new__(GroqClient)  # 略過 __init__ 的 OpenAI 連線
    from src.utils.logger import get_logger
    client.logger = get_logger("test")
    client.model = "test-model"

    def fake_chat(system, user, temperature=0.3, max_tokens=800):
        capture["system"] = system
        capture["user"] = user
        return "FAKE_RESPONSE"

    client._chat = fake_chat
    return client


def test_summarize_includes_title_and_abstract(monkeypatch):
    cap = {}
    client = _client(monkeypatch, cap)
    out = client.summarize(make_paper("1", "My Title", "My Abstract"))
    assert out == "FAKE_RESPONSE"
    assert "My Title" in cap["user"]
    assert "My Abstract" in cap["user"]


def test_answer_without_papers_short_circuits(monkeypatch):
    cap = {}
    client = _client(monkeypatch, cap)
    out = client.answer("任何問題", [])
    assert "知識庫" in out
    assert cap == {}  # 未呼叫 LLM


def test_answer_builds_context(monkeypatch):
    cap = {}
    client = _client(monkeypatch, cap)
    papers = [make_paper("1", "Paper A"), make_paper("2", "Paper B")]
    client.answer("問題", papers)
    assert "Paper A" in cap["user"] and "Paper B" in cap["user"]
    assert "問題" in cap["user"]


def test_research_report_without_papers(monkeypatch):
    cap = {}
    client = _client(monkeypatch, cap)
    out = client.research_report("some topic", [])
    assert "some topic" in out
    assert cap == {}
