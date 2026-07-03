"""NewsCrawler：RSS 解析（純函式）與 fetch（fake session），不打網路。"""
from src.crawlers.news_crawler import NewsCrawler, parse_rss, _strip_html

_SAMPLE_RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <title>AI News</title>
  <item>
    <title>New LLM released</title>
    <link>https://example.com/a</link>
    <description>&lt;p&gt;A big &lt;b&gt;model&lt;/b&gt;.&lt;/p&gt;</description>
    <pubDate>Wed, 01 Jul 2026 12:00:00 GMT</pubDate>
  </item>
  <item>
    <title>Agent framework launched</title>
    <link>https://example.com/b</link>
    <description>Details here</description>
    <pubDate>Thu, 02 Jul 2026 08:30:00 GMT</pubDate>
  </item>
</channel></rss>"""


class FakeResp:
    def __init__(self, text):
        self.text = text


class FakeSession:
    def __init__(self, text):
        self.text = text
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return FakeResp(self.text)


def test_strip_html():
    assert _strip_html("<p>hello <b>world</b></p>") == "hello world"


def test_parse_rss_extracts_items():
    items = parse_rss(_SAMPLE_RSS)
    assert len(items) == 2
    first = items[0]
    assert first["title"] == "New LLM released"
    assert first["link"] == "https://example.com/a"
    assert first["abstract"] == "A big model."          # HTML 被去除
    assert first["published"] == "2026-07-01"           # pubDate 解析
    assert first["source"] == "news"
    assert first["id"].startswith("news-")


def test_parse_rss_bad_xml_returns_empty():
    assert parse_rss("<not xml") == []


def test_fetch_ai_news_limit_and_headers():
    sess = FakeSession(_SAMPLE_RSS)
    crawler = NewsCrawler(feeds=["http://feed"], session=sess)
    items = crawler.fetch_ai_news(limit=1)
    assert len(items) == 1
    assert sess.calls[0]["headers"]["User-Agent"].startswith("RAGency")


def test_ids_are_stable_and_unique():
    items = parse_rss(_SAMPLE_RSS)
    assert items[0]["id"] != items[1]["id"]
    # 同連結應得到相同 id
    assert parse_rss(_SAMPLE_RSS)[0]["id"] == items[0]["id"]
