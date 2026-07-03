"""GitHub 熱門 AI repo 爬蟲：用公開 Search API 找近期快速成長（高星）的專案。

未帶 token 時仍可用（速率較低）；設定 GITHUB_TOKEN 可提高額度。
API：https://docs.github.com/en/rest/search/search#search-repositories
"""
from datetime import date, timedelta

import requests

from src.utils.logger import get_logger

_SEARCH = "https://api.github.com/search/repositories"


def _to_item(repo):
    """把 GitHub repo JSON 轉成統一結構。"""
    return {
        "id": f"gh-{repo['id']}",
        "title": repo.get("full_name", ""),
        "abstract": (repo.get("description") or repo.get("full_name") or "").strip(),
        "authors": (repo.get("owner") or {}).get("login", ""),
        "link": repo.get("html_url", ""),
        "published": (repo.get("created_at") or "")[:10],
        "source": "github",
        "stars": repo.get("stargazers_count", 0),
    }


class GitHubCrawler:
    def __init__(self, token=None, session=None):
        self.logger = get_logger(self.__class__.__name__)
        self.token = token
        self.session = session or requests

    def _headers(self):
        headers = {"Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def fetch_trending(self, topic="ai", days=30, limit=5, timeout=10):
        """找最近 days 天內建立、星數最高的相關 repo。"""
        since = (date.today() - timedelta(days=days)).isoformat()
        query = f"{topic} created:>{since}"
        params = {"q": query, "sort": "stars", "order": "desc", "per_page": limit}
        try:
            resp = self.session.get(
                _SEARCH, params=params, headers=self._headers(), timeout=timeout
            )
            data = resp.json()
        except Exception as e:
            self.logger.error(f"查詢 GitHub trending 失敗：{e}")
            return []

        items = [_to_item(r) for r in data.get("items", [])]
        self.logger.info(f"GitHub 取得 {len(items)} 個相關 repo（{query}）")
        return items[:limit]
