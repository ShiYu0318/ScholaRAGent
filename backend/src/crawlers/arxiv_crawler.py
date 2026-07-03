"""使用 arxiv 官方套件抓取最新論文（含摘要）。"""
import arxiv

from src.utils.logger import get_logger


class ArxivCrawler:
    def __init__(self, query="cat:cs.AI"):
        self.query = query
        self.client = arxiv.Client()
        self.logger = get_logger(self.__class__.__name__)

    def fetch_latest_papers(self, limit=5):
        """回傳最新論文清單（依投稿日期排序）。

        每篇為 dict：{id, title, abstract, authors, link, published}
        """
        return self._search(self.query, limit, arxiv.SortCriterion.SubmittedDate)

    def search_topic(self, topic, limit=8):
        """依主題搜尋最相關的論文（依相關度排序），供主題報告使用。"""
        # 將自然語言主題包成 arxiv 查詢：標題或摘要含關鍵字
        query = f'abs:"{topic}" OR ti:"{topic}"'
        return self._search(query, limit, arxiv.SortCriterion.Relevance)

    def _search(self, query, limit, sort_by):
        """以指定查詢與排序方式抓取論文。"""
        self.logger.info(f"查詢 arXiv: query='{query}' limit={limit} sort={sort_by}")
        search = arxiv.Search(query=query, max_results=limit, sort_by=sort_by)

        papers = []
        try:
            for result in self.client.results(search):
                papers.append({
                    "id": result.get_short_id(),
                    "title": result.title.strip(),
                    "abstract": result.summary.strip().replace("\n", " "),
                    "authors": ", ".join(a.name for a in result.authors[:5]),
                    "link": result.entry_id,
                    "published": result.published.strftime("%Y-%m-%d"),
                })
        except Exception as e:
            self.logger.error(f"抓取 arXiv 時發生錯誤: {e}", exc_info=True)

        self.logger.info(f"取得 {len(papers)} 篇論文")
        return papers
