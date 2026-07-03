"""Hacker News 爬蟲：用官方公開 Firebase API（免金鑰）抓熱門且與 AI 相關的貼文。

API 文件：https://github.com/HackerNews/API
"""
import re
from datetime import datetime, timezone

import requests

from src.utils.logger import get_logger

_TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
_ITEM = "https://hacker-news.firebaseio.com/v0/item/{}.json"

# 短詞用詞界比對，避免誤判（如 'email' 內含 'ai'）
_SHORT_TERMS = {"ai", "ml", "llm", "gpt", "rag", "genai", "agi"}
# 長詞/片語可直接子字串比對
_PHRASES = (
    "machine learning", "deep learning", "neural", "transformer", "diffusion",
    "agent", "openai", "anthropic", "claude", "gemini", "llama", "mistral",
    "embedding", "fine-tune", "fine tune", "inference", "language model",
    "reinforcement learning", "generative",
)


def is_ai_related(title):
    """標題是否與 AI 相關。短詞用詞界、片語用子字串比對。"""
    t = (title or "").lower()
    words = set(re.split(r"[^a-z0-9]+", t))
    if words & _SHORT_TERMS:
        return True
    return any(p in t for p in _PHRASES)


def _to_item(raw):
    """把 HN item JSON 轉成統一結構（對齊論文 schema，方便共用向量庫/DB）。"""
    ts = raw.get("time")
    published = (
        datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        if ts else ""
    )
    return {
        "id": f"hn-{raw['id']}",
        "title": (raw.get("title") or "").strip(),
        "abstract": (raw.get("text") or raw.get("title") or "").strip(),
        "authors": raw.get("by", ""),
        "link": raw.get("url") or f"https://news.ycombinator.com/item?id={raw['id']}",
        "published": published,
        "source": "hackernews",
        "score": raw.get("score", 0),
    }


class HackerNewsCrawler:
    def __init__(self, session=None):
        self.logger = get_logger(self.__class__.__name__)
        self.session = session or requests

    def fetch_ai_stories(self, limit=5, scan=100, timeout=10):
        """掃描前 scan 則熱門故事，回傳最多 limit 則與 AI 相關者（依分數排序）。"""
        try:
            ids = self.session.get(_TOP, timeout=timeout).json()[:scan]
        except Exception as e:
            self.logger.error(f"取得 HN 熱門清單失敗：{e}")
            return []

        items = []
        for sid in ids:
            try:
                raw = self.session.get(_ITEM.format(sid), timeout=timeout).json()
            except Exception as e:
                self.logger.error(f"取得 HN item {sid} 失敗：{e}")
                continue
            if not raw or raw.get("type") != "story" or not raw.get("title"):
                continue
            if is_ai_related(raw["title"]):
                items.append(_to_item(raw))
            if len(items) >= limit * 2:  # 多抓一些再依分數挑
                break

        items.sort(key=lambda it: it.get("score", 0), reverse=True)
        self.logger.info(f"HN 取得 {len(items)} 則 AI 相關貼文，回傳前 {limit} 則")
        return items[:limit]
