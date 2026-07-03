"""RedditCrawler：以 fake session 餵 Reddit .json 結構，測解析與排序（不打網路）。"""
from src.crawlers.reddit_crawler import RedditCrawler, _to_item


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        for needle, payload in self.routes:
            if needle in url:
                return FakeResponse(payload)
        raise AssertionError(f"未預期的 URL: {url}")


def _listing(posts):
    return {"data": {"children": [{"kind": "t3", "data": d} for d in posts]}}


def test_to_item_schema():
    item = _to_item({"id": "abc", "title": "Cool paper", "author": "bob",
                     "permalink": "/r/ML/comments/abc/cool/", "created_utc": 1_700_000_000,
                     "score": 42, "selftext": "details"})
    assert item["id"] == "reddit-abc"
    assert item["source"] == "reddit"
    assert item["link"] == "https://www.reddit.com/r/ML/comments/abc/cool/"
    assert item["abstract"] == "details"
    assert len(item["published"]) == 10


def test_fetch_top_parses_and_limits():
    posts = [{"id": str(i), "title": f"post {i}", "score": i, "created_utc": 1_700_000_000}
             for i in range(10)]
    sess = FakeSession([("r/MachineLearning/top.json", _listing(posts))])
    crawler = RedditCrawler(session=sess)
    items = crawler.fetch_top("MachineLearning", limit=3)
    assert len(items) == 3
    assert sess.calls[0]["headers"]["User-Agent"].startswith("RAGency")


def test_fetch_ai_discussions_merges_and_sorts():
    routes = [
        ("r/MachineLearning/top.json", _listing([{"id": "a", "title": "A", "score": 5, "created_utc": 1}])),
        ("r/LocalLLaMA/top.json", _listing([{"id": "b", "title": "B", "score": 50, "created_utc": 1}])),
        ("r/artificial/top.json", _listing([{"id": "c", "title": "C", "score": 20, "created_utc": 1}])),
    ]
    crawler = RedditCrawler(session=FakeSession(routes))
    items = crawler.fetch_ai_discussions(limit_per_sub=1)
    assert [it["id"] for it in items] == ["reddit-b", "reddit-c", "reddit-a"]  # 依分數排序
