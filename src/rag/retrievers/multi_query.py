"""多查詢檢索（Advanced RAG / A2 收尾）：把查詢轉換接進實際檢索。

流程：先用 QueryTransformer 把問題改寫成多個版本（含原查詢），
每個版本各自檢索，最後用 Reciprocal Rank Fusion 融合成單一排序。
好處是涵蓋不同措辭與角度，補足單一查詢的召回死角。

`base_retrieve` 是任何 `retrieve(query, k) -> [(paper, score)]` 的可呼叫物件，
例如 HybridRetriever.retrieve，或退化為 VectorStore.search_scored。
"""
from src.rag.retrievers.hybrid import reciprocal_rank_fusion
from src.utils.logger import get_logger


class MultiQueryRetriever:
    def __init__(self, transformer, base_retrieve, rrf_k=60):
        self.logger = get_logger(self.__class__.__name__)
        self.transformer = transformer
        self.base_retrieve = base_retrieve
        self.rrf_k = rrf_k

    def retrieve(self, query, k=4, n_variants=3, fetch=None):
        """回傳 [(paper, fused_score)]，融合各改寫版本的檢索結果。"""
        fetch = fetch or max(k * 3, 10)
        variants = self.transformer.multi_query(query, n=n_variants)

        by_id = {}
        ranked_id_lists = []
        for v in variants:
            hits = self.base_retrieve(v, k=fetch)
            ids = []
            for paper, _ in hits:
                by_id.setdefault(paper["id"], paper)
                ids.append(paper["id"])
            ranked_id_lists.append(ids)

        fused = reciprocal_rank_fusion(ranked_id_lists, k=self.rrf_k)
        self.logger.info(f"多查詢檢索：{len(variants)} 版本 → 融合 {len(fused)} 篇候選")
        return [(by_id[pid], score) for pid, score in fused[:k] if pid in by_id]

    def search(self, query, k=4, n_variants=3):
        """向後相容：只回傳論文 dict 清單。"""
        return [p for p, _ in self.retrieve(query, k=k, n_variants=n_variants)]
