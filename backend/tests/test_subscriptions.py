"""訂閱式主題快報，JSON 持久化。"""
from src.recommend.subscriptions import Subscriptions


def _paper(title, abstract=""):
    return {"title": title, "abstract": abstract}


def test_add_and_match_by_keyword(tmp_path):
    s = Subscriptions(tmp_path / "s.json")
    s.add("rag", ["retrieval", "rag"])
    s.add("gnn", ["graph neural"])
    hits = s.matches(_paper("A RAG survey", "retrieval augmented generation"))
    assert "rag" in hits and "gnn" not in hits


def test_match_is_case_insensitive(tmp_path):
    s = Subscriptions(tmp_path / "s.json")
    s.add("t", ["Transformer"])
    assert "t" in s.matches(_paper("about transformers"))


def test_persists_across_instances(tmp_path):
    path = tmp_path / "s.json"
    Subscriptions(path).add("rag", ["rag"])
    assert "rag" in {sub["name"] for sub in Subscriptions(path).all()}


def test_no_match_returns_empty(tmp_path):
    s = Subscriptions(tmp_path / "s.json")
    s.add("rag", ["rag"])
    assert s.matches(_paper("quantum computing")) == []
