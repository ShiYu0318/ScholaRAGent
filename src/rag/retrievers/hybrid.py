"""混合檢索：以 Reciprocal Rank Fusion (RRF) 融合稠密（向量）與稀疏（BM25）結果。

RRF 只依「名次」融合，不需校正不同檢索器的分數尺度，穩健且實務常用。
"""
from src.rag.retrievers.bm25 import BM25Index
from src.utils.logger import get_logger


def reciprocal_rank_fusion(ranked_id_lists, k=60):
    """輸入多個「已排序的 id 清單」，回傳 [(id, fused_score)] 依融合分數排序。"""
    scores = {}
    for ids in ranked_id_lists:
        for rank, key in enumerate(ids):
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda it: it[1], reverse=True)


class HybridRetriever:
    def __init__(self, vector_store, bm25=None, rrf_k=60):
        self.logger = get_logger(self.__class__.__name__)
        self.vs = vector_store
        self.bm25 = bm25 or BM25Index()
        self.rrf_k = rrf_k
        self._fitted = False

    def index(self):
        """（重）建 BM25 索引，對齊向量庫目前的論文。"""
        self.bm25.fit(self.vs.papers)
        self._fitted = True
        return self

    def retrieve(self, query, k=5, where=None, fetch=20):
        """回傳 [(paper, fused_score)]，結合稠密與稀疏檢索。"""
        if not self._fitted:
            self.index()

        dense = self.vs.search_scored(query, k=fetch, where=where, rerank=False)
        sparse = self.bm25.search(query, k=fetch)
        if where is not None:
            sparse = [(p, s) for p, s in sparse if where(p)]

        by_id = {}
        for p, _ in dense:
            by_id[p["id"]] = p
        for p, _ in sparse:
            by_id.setdefault(p["id"], p)

        fused = reciprocal_rank_fusion(
            [[p["id"] for p, _ in dense], [p["id"] for p, _ in sparse]],
            k=self.rrf_k,
        )
        return [(by_id[pid], score) for pid, score in fused[:k] if pid in by_id]
