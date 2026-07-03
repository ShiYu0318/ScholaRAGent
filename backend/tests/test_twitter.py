"""TwitterCrawler：enabled 判定、API v2 解析、無 token 安全略過（不打網路）。"""
from src.crawlers.twitter_crawler import TwitterCrawler, _to_item


class FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return FakeResp(self.payload)


def test_disabled_without_token():
    assert TwitterCrawler().enabled is False
    assert TwitterCrawler(bearer_token="t").enabled is True


def test_fetch_skipped_without_token():
    sess = FakeSession({})
    crawler = TwitterCrawler(session=sess)
    assert crawler.fetch_recent() == []
    assert sess.calls == []  # 未打 API


def test_to_item_schema():
    item = _to_item({"id": "123", "text": "AI is cool", "author_id": "u1",
                     "created_at": "2026-07-01T10:00:00.000Z"})
    assert item["id"] == "x-123"
    assert item["source"] == "twitter"
    assert item["link"] == "https://twitter.com/i/web/status/123"
    assert item["published"] == "2026-07-01"


def test_fetch_parses_and_sets_auth_header():
    payload = {"data": [
        {"id": "1", "text": "post one", "author_id": "a", "created_at": "2026-07-01T00:00:00Z"},
        {"id": "2", "text": "post two", "author_id": "b", "created_at": "2026-07-01T00:00:00Z"},
    ]}
    sess = FakeSession(payload)
    crawler = TwitterCrawler(bearer_token="TOK", session=sess)
    items = crawler.fetch_recent(limit=1)
    assert len(items) == 1
    assert items[0]["id"] == "x-1"
    assert sess.calls[0]["headers"]["Authorization"] == "Bearer TOK"
    assert sess.calls[0]["params"]["max_results"] >= 10  # API 下限
