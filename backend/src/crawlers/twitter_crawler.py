"""X (Twitter) 爬蟲：官方 API v2 recent search。需 X_BEARER_TOKEN。

註：X 已於 2023 起取消免費讀取層，recent search 需付費方案的 bearer token。
未設定 token 時 enabled=False，會安全略過（不報錯）。
"""
from datetime import datetime, timezone

import requests

from src.utils.logger import get_logger

_SEARCH = "https://api.twitter.com/2/tweets/search/recent"


def _to_item(tweet):
    """把 tweet 物件轉成統一 schema。"""
    created = tweet.get("created_at", "")
    published = ""
    if created:
        try:
            published = datetime.fromisoformat(
                created.replace("Z", "+00:00")
            ).astimezone(timezone.utc).strftime("%Y-%m-%d")
        except ValueError:
            published = created[:10]
    text = (tweet.get("text") or "").strip()
    tid = tweet.get("id", "")
    return {
        "id": f"x-{tid}",
        "title": text[:120],
        "abstract": text,
        "authors": tweet.get("author_id", ""),
        "link": f"https://twitter.com/i/web/status/{tid}",
        "published": published,
        "source": "twitter",
    }


class TwitterCrawler:
    def __init__(self, bearer_token=None, session=None):
        self.logger = get_logger(self.__class__.__name__)
        self.bearer_token = bearer_token
        self.session = session or requests

    @property
    def enabled(self):
        return bool(self.bearer_token)

    def fetch_recent(self, query="artificial intelligence -is:retweet lang:en",
                     limit=5, timeout=10):
        if not self.enabled:
            self.logger.info("X_BEARER_TOKEN 未設定，略過 X 爬蟲")
            return []
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        params = {
            "query": query,
            "max_results": max(10, min(limit, 100)),  # API 下限 10
            "tweet.fields": "created_at,author_id",
        }
        try:
            resp = self.session.get(_SEARCH, params=params, headers=headers, timeout=timeout)
            data = resp.json().get("data", [])
        except Exception as e:
            self.logger.error(f"X 查詢失敗：{e}")
            return []
        items = [_to_item(t) for t in data]
        self.logger.info(f"X 取得 {len(items)} 則貼文，回傳前 {limit} 則")
        return items[:limit]
