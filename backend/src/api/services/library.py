"""文庫服務：論文清單/詳情（可信度、可重現）、每日抓取、個人化、
RSS feeds 刷新、匯出（Obsidian/CSV/BibTeX）。

爬蟲與 OpenAlex 可注入替身；credibility 需逐篇打 OpenAlex，只在單篇
詳情做，清單只附零成本的 reproducibility（regex 抽 code 連結）。
"""
import csv
import io
import threading

from src import config
from src.crawlers.arxiv_crawler import ArxivCrawler
from src.crawlers.news_crawler import NewsCrawler
from src.crawlers.openalex import OpenAlexClient
from src.recommend.credibility import credibility_signal
from src.recommend.personalize import personalize_daily
from src.recommend.ranker import rank_papers
from src.recommend.reproducibility import reproducibility_signal
from src.tools.obsidian_export import to_obsidian
from src.tools.research_tools import to_bibtex
from src.utils.logger import get_logger

CSV_FIELDS = ("id", "title", "authors", "published", "link", "source", "summary")


class LibraryService:
    def __init__(self, store, arxiv=None, news=None, openalex=None, embedder=None):
        self.logger = get_logger(self.__class__.__name__)
        self.store = store
        self._arxiv = arxiv
        self._news = news or NewsCrawler()
        self._openalex = openalex
        self._embedder = embedder

    @property
    def arxiv(self):
        if self._arxiv is None:
            self._arxiv = ArxivCrawler(query=config.ARXIV_QUERY)
        return self._arxiv

    @property
    def openalex(self):
        if self._openalex is None:
            self._openalex = OpenAlexClient()
        return self._openalex

    @property
    def embedder(self):
        if self._embedder is None:
            self._embedder = self.store.vector.embedder
        return self._embedder

    # ---- 論文 ----
    def papers(self, limit=50, source=None, query=None):
        items = self.store.all_papers(source=source)
        if query:
            q = query.lower()
            items = [p for p in items
                     if q in (p.get("title") or "").lower()
                     or q in (p.get("abstract") or "").lower()]
        total = len(items)
        items = items[:limit]
        for p in items:
            p["reproducibility"] = reproducibility_signal(p)
        return {"items": items, "total": total}

    def paper(self, paper_id):
        p = self.store.get_paper(paper_id)
        if p is None:
            return None
        p["reproducibility"] = reproducibility_signal(p)
        try:
            p["credibility"] = credibility_signal(p, self.openalex)
        except Exception as e:
            self.logger.info(f"credibility 查詢失敗：{e}")
            p["credibility"] = None
        return p

    # ---- 每日抓取 ----
    def daily(self, count=None):
        """抓最新論文入庫並建向量索引，回傳實際新增清單。"""
        papers = self.arxiv.fetch_latest_papers(limit=count or config.DAILY_COUNT)
        added = self.store.upsert_papers(papers)
        indexed = self.store.index_papers(papers)
        self.logger.info(f"每日抓取：{len(papers)} 篇，新增 {added}，索引 {len(indexed)}")
        return {"fetched": len(papers), "added": added, "items": papers}

    def personalized(self, user_id, top_n=5, pool=50):
        """依互動輪廓（問過/按讚的論文標題 + 訂閱關鍵字）排序近期論文。"""
        pool_papers = self.store.all_papers(limit=pool)
        profile = []
        for it in self.store.user_interactions(user_id, limit=100):
            if it.get("paper_id"):
                p = self.store.get_paper(it["paper_id"])
                if p:
                    profile.append(p["title"])
        for sub in self.store.list_subscriptions(user_id):
            profile.extend(sub["keywords"])
        if not profile:
            counts = self.store.interaction_counts()
            return rank_papers(pool_papers, interaction_counts=counts)[:top_n]
        return personalize_daily(pool_papers, profile, self.embedder, top_n=top_n)

    # ---- RSS feeds ----
    def refresh_feeds(self, user_id):
        """抓使用者所有啟用的 RSS 來源，入庫（source=rss）並索引。"""
        feeds = [f for f in self.store.list_feeds(user_id) if f["enabled"]]
        fetched, added = 0, 0
        for feed in feeds:
            items = self._news.fetch_feed(feed["url"])
            for it in items:
                it["source"] = "rss"
            fetched += len(items)
            added += self.store.upsert_papers(items)
            if items:
                self.store.index_papers(items)
        return {"feeds": len(feeds), "fetched": fetched, "added": added}

    # ---- 匯出 ----
    def export_csv(self, limit=1000):
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for p in self.store.all_papers(limit=limit):
            writer.writerow({k: p.get(k, "") or "" for k in CSV_FIELDS})
        return buf.getvalue()

    def export_bibtex(self, limit=1000):
        return to_bibtex(self.store.all_papers(limit=limit))

    def export_obsidian(self, limit=200):
        """回傳 {filename: markdown}；zip 打包由 router 處理。"""
        return to_obsidian(self.store.all_papers(limit=limit))


_service = None
_service_lock = threading.Lock()


def get_library_service():
    global _service
    with _service_lock:
        if _service is None:
            from src.store import get_store
            _service = LibraryService(get_store())
    return _service


def set_library_service(service):
    """測試注入；回傳先前實例。"""
    global _service
    prev, _service = _service, service
    return prev
