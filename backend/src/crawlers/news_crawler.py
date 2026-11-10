"""AI 新聞爬蟲：解析公開 RSS/Atom feed（免憑證）。

預設用 Google News 的 RSS 搜尋端點（公開），可在 config 覆寫 feed 清單。
"""
import hashlib
import re
from email.utils import parsedate_to_datetime

import requests
from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException

from src.utils.logger import get_logger
from src.utils.safe_http import UnsafeURLError, safe_get
from src.utils.text_safety import safe_link

_UA = "ScholaRAGent/1.0 (news reader)"
_DEFAULT_FEEDS = (
    "https://news.google.com/rss/search?q=artificial+intelligence&hl=en-US&gl=US&ceid=US:en",
)
_TAG = re.compile(r"<[^>]+>")
MAX_ITEMS_PER_FEED = 50
MAX_TITLE = 500
MAX_ABSTRACT = 5000


def _strip_html(text):
    return _TAG.sub("", text or "").strip()


def _short_id(link):
    return "news-" + hashlib.sha1((link or "").encode("utf-8")).hexdigest()[:10]


def _parse_date(raw):
    if not raw:
        return ""
    try:
        return parsedate_to_datetime(raw).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return raw[:10]


def parse_rss(xml_text):
    """把 RSS/Atom XML 解析成統一 item 清單（純函式，離線可測）。"""
    # defusedxml：拒絕實體展開（billion laughs）與外部實體（XXE）
    try:
        root = ET.fromstring(xml_text)
    except (ET.ParseError, DefusedXmlException, ValueError):
        return []

    items = []
    # RSS 2.0：channel/item
    for item in root.iter("item"):
        title = item.findtext("title", "")
        link = item.findtext("link", "")
        desc = item.findtext("description", "")
        pub = item.findtext("pubDate", "")
        if not title:
            continue
        if len(items) >= MAX_ITEMS_PER_FEED:
            break
        items.append({
            "id": _short_id(link),
            "title": title.strip()[:MAX_TITLE],
            "abstract": (_strip_html(desc) or title.strip())[:MAX_ABSTRACT],
            "authors": "",
            "link": safe_link(link),
            "published": _parse_date(pub),
            "source": "news",
        })
    return items


class NewsCrawler:
    def __init__(self, feeds=None, session=None, resolver=None):
        self.logger = get_logger(self.__class__.__name__)
        self.feeds = list(feeds) if feeds else list(_DEFAULT_FEEDS)
        self.session = session or requests
        self._resolver = resolver  # 測試注入 DNS 解析

    def fetch_feed(self, url, timeout=10):
        """抓一個 feed。URL 可能來自使用者，一律走 safe_get（擋內網位址、限制大小）。"""
        try:
            text = safe_get(url, headers={"User-Agent": _UA}, timeout=timeout,
                            session=self.session, resolver=self._resolver)
            return parse_rss(text)
        except UnsafeURLError as e:
            self.logger.warning(f"拒絕抓取 feed（{url}）：{e}")
            return []
        except Exception as e:
            self.logger.error(f"抓取新聞 feed 失敗（{url}）：{e}")
            return []

    def fetch_ai_news(self, limit=5):
        """跨所有 feed 抓 AI 新聞，回傳前 limit 則。"""
        items = []
        for feed in self.feeds:
            items.extend(self.fetch_feed(feed))
        self.logger.info(f"新聞取得 {len(items)} 則，回傳前 {limit} 則")
        return items[:limit]
