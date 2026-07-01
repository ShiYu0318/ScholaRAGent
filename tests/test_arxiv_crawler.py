"""ArxivCrawler：查詢字串與排序組裝（monkeypatch _search，避免打網路）。"""
import arxiv

from src.crawlers.arxiv_crawler import ArxivCrawler


def _patched():
    crawler = ArxivCrawler(query="cat:cs.AI")
    calls = {}

    def fake_search(query, limit, sort_by):
        calls["query"] = query
        calls["limit"] = limit
        calls["sort_by"] = sort_by
        return []

    crawler._search = fake_search
    return crawler, calls


def test_fetch_latest_uses_submitted_date():
    crawler, calls = _patched()
    crawler.fetch_latest_papers(limit=7)
    assert calls["query"] == "cat:cs.AI"
    assert calls["limit"] == 7
    assert calls["sort_by"] == arxiv.SortCriterion.SubmittedDate


def test_search_topic_builds_query_and_relevance():
    crawler, calls = _patched()
    crawler.search_topic("multi agent RL", limit=5)
    assert 'abs:"multi agent RL"' in calls["query"]
    assert 'ti:"multi agent RL"' in calls["query"]
    assert calls["sort_by"] == arxiv.SortCriterion.Relevance
    assert calls["limit"] == 5
