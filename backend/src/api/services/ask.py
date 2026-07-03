"""問答服務：adaptive 複雜度分派 + 混合/多查詢檢索（可選精排）+ 串流生成。

重用 bot 的檢索堆疊，但以 Store 介面為底（SQLite/FAISS 與 Postgres/pgvector
都能跑）。LLM 可注入替身，離線測試不打外部服務。
"""
import threading

from src import config
from src.agent.adaptive_rag import classify_complexity
from src.llm.groq_client import GroqClient
from src.rag.query_transform import QueryTransformer
from src.rag.retrievers.hybrid import HybridRetriever
from src.rag.retrievers.multi_query import MultiQueryRetriever
from src.utils.logger import get_logger


class _StoreVectorAdapter:
    """讓 HybridRetriever 能吃 Store 介面（.papers 與 .search_scored）。"""

    def __init__(self, store):
        self._store = store

    @property
    def papers(self):
        return self._store.all_papers()

    def search_scored(self, query, k=4, where=None, rerank=True):
        return self._store.search_scored(query, k=k, where=where, rerank=rerank)


class AskService:
    def __init__(self, store, llm=None, reranker=None):
        self.logger = get_logger(self.__class__.__name__)
        self.store = store
        self._llm = llm
        self._lock = threading.Lock()
        adapter = _StoreVectorAdapter(store)
        self.hybrid = HybridRetriever(adapter)
        self._reranker = reranker
        self._transformer = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = GroqClient()
        return self._llm

    @property
    def transformer(self):
        if self._transformer is None:
            self._transformer = QueryTransformer(self.llm)
        return self._transformer

    @property
    def reranker(self):
        if self._reranker is None and config.RERANK_ENABLED:
            from src.rag.retrievers.reranker import CrossEncoderReranker
            self._reranker = CrossEncoderReranker()
        return self._reranker

    def _simple_search(self, question, k=4):
        with self._lock:
            self.hybrid.index()
            hits = self.hybrid.retrieve(question, k=k)
        return [p for p, _ in hits]

    def _multi_search(self, question, k=4):
        with self._lock:
            self.hybrid.index()
            retriever = MultiQueryRetriever(self.transformer, self.hybrid.retrieve)
            if self.reranker is not None:
                cands = retriever.search(question, k=max(k * 3, 10))
                return [p for p, _ in self.reranker.rerank(question, cands, k=k)]
            return retriever.search(question, k=k)

    def retrieve(self, question, k=4):
        """adaptive：none 不檢索、simple 混合檢索、complex 多查詢（+可選精排）。"""
        if self.store.count_papers() == 0:
            return []
        level = classify_complexity(question)
        if level == "none":
            return []
        if level == "complex":
            return self._multi_search(question, k=k)
        return self._simple_search(question, k=k)

    @staticmethod
    def citations(papers):
        """整理給前端的引用 payload。"""
        return [
            {
                "id": p.get("id"),
                "title": p.get("title", ""),
                "link": p.get("link", ""),
                "published": p.get("published", ""),
                "authors": p.get("authors", ""),
            }
            for p in papers
        ]

    def stream(self, question, papers):
        """逐字產生回答。"""
        yield from self.llm.stream_answer(question, papers)


_service = None
_service_lock = threading.Lock()


def get_ask_service():
    global _service
    with _service_lock:
        if _service is None:
            from src.store import get_store
            _service = AskService(get_store())
    return _service


def set_ask_service(service):
    """測試注入；回傳先前實例。"""
    global _service
    prev, _service = _service, service
    return prev
