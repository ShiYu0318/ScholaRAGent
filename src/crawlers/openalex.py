"""OpenAlex 引用資料 client（GraphRAG / C1）。

OpenAlex 是免費、免金鑰的學術圖譜。以 arXiv 論文的 DOI（10.48550/arXiv.<id>）
查詢，取得被引數與參考文獻，供引用圖（C1）、可信度訊號（D9）使用。

`fetch(url) -> dict` 可注入，離線用 stub 測試；預設用 requests 實打 API。
禮貌起見可帶 mailto 進入 OpenAlex 的 polite pool。
"""
import re

from src.utils.logger import get_logger

_VERSION = re.compile(r"v\d+$")
_OA_PREFIX = "https://openalex.org/"


def _default_fetch(url):
    import requests
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.json()


def _strip_oa(ref):
    return ref[len(_OA_PREFIX):] if ref.startswith(_OA_PREFIX) else ref


class OpenAlexClient:
    BASE = "https://api.openalex.org"

    def __init__(self, fetch=None, mailto=None):
        self.logger = get_logger(self.__class__.__name__)
        self._fetch = fetch or _default_fetch
        self.mailto = mailto

    _SELECT = "id,title,cited_by_count,referenced_works,publication_year"

    def _url(self, path):
        url = f"{self.BASE}/{path}"
        sep = "&" if "?" in url else "?"
        url += f"{sep}select={self._SELECT}"
        if self.mailto:
            url += f"&mailto={self.mailto}"
        return url

    def _normalize(self, data):
        if not data or "id" not in data:
            return None
        return {
            "openalex_id": _strip_oa(data["id"]),
            "title": data.get("title", ""),
            "cited_by_count": data.get("cited_by_count", 0),
            "year": data.get("publication_year"),
            "references": [_strip_oa(r) for r in data.get("referenced_works", [])],
        }

    def work_by_arxiv(self, arxiv_id, title=None):
        """以 arXiv id 查 work（DOI 直查）；查不到且有 title 時退回標題搜尋。"""
        clean = _VERSION.sub("", (arxiv_id or "").strip().replace("arXiv:", ""))
        try:
            data = self._fetch(self._url(f"works/doi:10.48550/arXiv.{clean}"))
            work = self._normalize(data)
        except Exception as e:
            # 舊論文常無 arXiv DOI（2022 前），或被限流 → 退回標題搜尋
            self.logger.info(f"OpenAlex DOI 查詢未果（{clean}）：{e}")
            work = None
        if work is None and title:
            return self.work_by_title(title)
        return work

    def work_by_title(self, title):
        """以標題搜尋 work（搜尋端點；匿名可能被限流，失敗回 None）。"""
        from urllib.parse import quote
        try:
            data = self._fetch(self._url(f"works?filter=title.search:{quote(title)}&per-page=1"))
            results = (data or {}).get("results", [])
            return self._normalize(results[0]) if results else None
        except Exception as e:
            self.logger.info(f"OpenAlex 標題搜尋未果（{title[:40]}）：{e}")
            return None

    def cited_by(self, openalex_id, limit=25):
        """回傳引用此 work 的論文（derivative works），正規化清單。失敗回空。"""
        per = min(max(limit, 1), 200)
        try:
            data = self._fetch(self._url(f"works?filter=cites:{openalex_id}&per-page={per}"))
        except Exception as e:
            self.logger.info(f"OpenAlex cited_by 查詢未果（{openalex_id}）：{e}")
            return []
        works = [self._normalize(w) for w in (data or {}).get("results", [])]
        return [w for w in works if w][:limit]

    def citation_count(self, arxiv_id, title=None):
        """便捷：只取被引數；查不到回 0。"""
        w = self.work_by_arxiv(arxiv_id, title=title)
        return w["cited_by_count"] if w else 0
