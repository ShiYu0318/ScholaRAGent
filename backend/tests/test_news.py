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
    status_code = 200
    encoding = "utf-8"
    headers = {}

    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size=65536):
        yield self.text.encode("utf-8")

    def close(self):
        pass


def _public(host, port):
    return {"93.184.216.34"}


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
    crawler = NewsCrawler(feeds=["http://feed.example.com"], session=sess, resolver=_public)
    items = crawler.fetch_ai_news(limit=1)
    assert len(items) == 1
    assert sess.calls[0]["headers"]["User-Agent"].startswith("ScholaRAGent")


def test_ids_are_stable_and_unique():
    items = parse_rss(_SAMPLE_RSS)
    assert items[0]["id"] != items[1]["id"]
    # 同連結應得到相同 id
    assert parse_rss(_SAMPLE_RSS)[0]["id"] == items[0]["id"]


def test_fetch_feed_refuses_internal_address():
    sess = FakeSession(_SAMPLE_RSS)
    crawler = NewsCrawler(session=sess, resolver=lambda h, p: {"10.0.0.5"})
    assert crawler.fetch_feed("http://intranet.example.com/rss") == []
    assert sess.calls == []          # 根本沒有送出請求


def test_parse_rss_rejects_entity_expansion():
    bomb = """<?xml version="1.0"?>
<!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;&lol;&lol;">]>
<rss><channel><item><title>&lol2;</title><link>https://e.com/x</link></item></channel></rss>"""
    assert parse_rss(bomb) == []


def test_parse_rss_drops_non_http_links():
    xml = """<rss><channel><item><title>T</title>
<link>javascript:alert(1)</link></item></channel></rss>"""
    assert parse_rss(xml)[0]["link"] == ""


def test_parse_rss_caps_item_count():
    from src.crawlers.news_crawler import MAX_ITEMS_PER_FEED
    body = "".join(f"<item><title>t{i}</title><link>https://e.com/{i}</link></item>"
                   for i in range(MAX_ITEMS_PER_FEED + 20))
    assert len(parse_rss(f"<rss><channel>{body}</channel></rss>")) == MAX_ITEMS_PER_FEED
