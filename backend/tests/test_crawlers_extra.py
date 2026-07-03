"""HackerNews / GitHub 爬蟲：以 fake session 餵 JSON，測解析與過濾（不打網路）。"""
from src.crawlers.hackernews_crawler import HackerNewsCrawler, is_ai_related, _to_item
from src.crawlers import hackernews_crawler as hn
from src.crawlers.github_crawler import GitHubCrawler


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class FakeSession:
    """依 URL 回傳預先準備的 JSON。"""
    def __init__(self, routes):
        self.routes = routes  # list of (substring, payload)

    def get(self, url, **kwargs):
        for needle, payload in self.routes:
            if needle in url:
                return FakeResponse(payload)
        raise AssertionError(f"未預期的 URL: {url}")


# ---- is_ai_related ----
def test_is_ai_related_short_terms():
    assert is_ai_related("New LLM beats GPT-4")
    assert is_ai_related("An AI agent for coding")
    assert not is_ai_related("How to bake sourdough bread")
    # 'email' 不應因含 'ai' 被誤判
    assert not is_ai_related("A better email client")


def test_is_ai_related_phrases():
    assert is_ai_related("Reinforcement learning at scale")
    assert is_ai_related("Diffusion models for audio")


def test_hn_to_item_schema():
    raw = {"id": 42, "title": "Cool LLM", "by": "alice", "url": "http://x",
           "time": 1_700_000_000, "type": "story", "score": 99}
    item = _to_item(raw)
    assert item["id"] == "hn-42"
    assert item["source"] == "hackernews"
    assert item["link"] == "http://x"
    assert len(item["published"]) == 10


def test_hn_fetch_filters_and_ranks(monkeypatch):
    routes = [
        (hn._TOP.split("?")[0] if "?" in hn._TOP else "topstories", [1, 2, 3]),
        ("item/1", {"id": 1, "title": "AI breakthrough", "type": "story", "score": 10, "time": 1700000000}),
        ("item/2", {"id": 2, "title": "Cooking tips", "type": "story", "score": 500, "time": 1700000000}),
        ("item/3", {"id": 3, "title": "New GPT model", "type": "story", "score": 50, "time": 1700000000}),
    ]
    crawler = HackerNewsCrawler(session=FakeSession(routes))
    items = crawler.fetch_ai_stories(limit=5, scan=3)
    titles = [i["title"] for i in items]
    assert "Cooking tips" not in titles           # 非 AI 被濾掉
    assert titles == ["New GPT model", "AI breakthrough"]  # 依分數排序


def test_github_to_item_and_fetch():
    payload = {"items": [
        {"id": 7, "full_name": "org/agent-lib", "description": "An AI agent framework",
         "owner": {"login": "org"}, "html_url": "http://gh/agent",
         "created_at": "2026-06-01T00:00:00Z", "stargazers_count": 1234},
    ]}
    routes = [("search/repositories", payload)]
    crawler = GitHubCrawler(session=FakeSession(routes))
    items = crawler.fetch_trending(topic="agent", limit=5)
    assert len(items) == 1
    assert items[0]["id"] == "gh-7"
    assert items[0]["source"] == "github"
    assert items[0]["stars"] == 1234
    assert items[0]["published"] == "2026-06-01"
