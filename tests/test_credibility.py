"""可信度／影響力訊號（v2/D9），離線 stub client。"""
from src.recommend.credibility import credibility_signal, annotate_credibility, format_signal


def _paper(pid="1", title="T"):
    return {"id": pid, "title": title}


class StubClient:
    def __init__(self, count, found=True):
        self.count = count
        self.found = found

    def work_by_arxiv(self, arxiv_id, title=None):
        if not self.found:
            return None
        return {"cited_by_count": self.count, "openalex_id": "W1", "references": []}


def test_high_impact_tier():
    sig = credibility_signal(_paper(), StubClient(500))
    assert sig["cited_by_count"] == 500
    assert sig["tier"] == "high"


def test_medium_and_low_tiers():
    assert credibility_signal(_paper(), StubClient(50))["tier"] == "medium"
    assert credibility_signal(_paper(), StubClient(2))["tier"] == "low"


def test_missing_work_defaults_to_zero():
    sig = credibility_signal(_paper(), StubClient(0, found=False))
    assert sig["cited_by_count"] == 0 and sig["tier"] == "low"


def test_annotate_attaches_signal_to_papers():
    papers = [_paper("1"), _paper("2")]
    out = annotate_credibility(papers, StubClient(120))
    assert all("credibility" in p for p in out)
    assert out[0]["credibility"]["tier"] == "high"


def test_format_signal_readable():
    s = format_signal({"cited_by_count": 300, "tier": "high"})
    assert "300" in s
