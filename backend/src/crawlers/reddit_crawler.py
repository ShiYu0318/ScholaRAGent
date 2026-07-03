"""Reddit 爬蟲：用公開 .json 端點抓熱門討論（讀取免 OAuth，但需自訂 User-Agent）。

預設抓 AI 相關 subreddit 的本週熱門貼文。X (Twitter) 無免費公開讀取 API，仍需憑證，另議。
"""
from datetime import datetime, timezone

import requests

from src.utils.logger import get_logger

_UA = "RAGency/1.0 (research reader)"
_DEFAULT_SUBS = ("MachineLearning", "LocalLLaMA", "artificial")


def _to_item(data):
    """把 Reddit post 的 data 物件轉成統一結構。"""
    ts = data.get("created_utc")
    published = (
        datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        if ts else ""
    )
    permalink = data.get("permalink", "")
    return {
        "id": f"reddit-{data.get('id', '')}",
        "title": (data.get("title") or "").strip(),
        "abstract": (data.get("selftext") or data.get("title") or "").strip()[:2000],
        "authors": data.get("author", ""),
        "link": f"https://www.reddit.com{permalink}" if permalink else data.get("url", ""),
        "published": published,
        "source": "reddit",
        "score": data.get("score", 0),
    }


class RedditCrawler:
    def __init__(self, subreddits=None, session=None):
        self.logger = get_logger(self.__class__.__name__)
        self.subreddits = subreddits or list(_DEFAULT_SUBS)
        self.session = session or requests

    def fetch_top(self, subreddit, limit=5, period="week", timeout=10):
        """抓單一 subreddit 的熱門貼文。"""
        url = f"https://www.reddit.com/r/{subreddit}/top.json"
        params = {"t": period, "limit": limit}
        try:
            resp = self.session.get(
                url, params=params, headers={"User-Agent": _UA}, timeout=timeout
            )
            children = resp.json().get("data", {}).get("children", [])
        except Exception as e:
            self.logger.error(f"抓取 r/{subreddit} 失敗：{e}")
            return []
        items = [_to_item(c.get("data", {})) for c in children if c.get("kind") == "t3"]
        return items[:limit]

    def fetch_ai_discussions(self, limit_per_sub=3):
        """跨預設 AI subreddit 抓熱門討論，合併後依分數排序。"""
        items = []
        for sub in self.subreddits:
            items.extend(self.fetch_top(sub, limit=limit_per_sub))
        items.sort(key=lambda it: it.get("score", 0), reverse=True)
        self.logger.info(f"Reddit 取得 {len(items)} 則 AI 討論")
        return items
