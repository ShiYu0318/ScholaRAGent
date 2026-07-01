"""BGE cross-encoder 重排序（Advanced RAG / A3）。

第一階段（向量 + BM25 混合）先過取候選，這裡用 cross-encoder 對
(query, 文件) 直接打分做精排——比雙塔嵌入更準，但較慢，故只排前段候選。

預設模型 `BAAI/bge-reranker-v2-m3`（多語）。`scorer` 可注入，方便離線
stub 測試；失敗時優雅退回原順序（與專案其他模組一致）。
"""
from src import config
from src.utils.logger import get_logger


class CrossEncoderReranker:
    def __init__(self, model_name=None, scorer=None):
        self.logger = get_logger(self.__class__.__name__)
        self.model_name = model_name or config.RERANK_MODEL
        self._scorer = scorer   # callable(pairs) -> list[float]；None 表示延遲載入真模型
        self._model = None

    def _score(self, pairs):
        """對 [(query, doc), ...] 回傳分數清單。"""
        if self._scorer is not None:
            return self._scorer(pairs)
        if self._model is None:
            from sentence_transformers import CrossEncoder
            self.logger.info(f"載入 reranker 模型: {self.model_name}")
            self._model = CrossEncoder(self.model_name)
        return self._model.predict(pairs)

    def rerank(self, query, candidates, k=None):
        """依 cross-encoder 分數重排 candidates（[(paper, prior_score)]）。

        回傳 [(paper, ce_score)]（分數越高越相關），取前 k。
        scorer 失敗時退回原傳入順序。
        """
        if not candidates:
            return []

        papers = [p for p, _ in candidates]
        pairs = [(query, f"{p.get('title', '')}. {p.get('abstract', '')}".strip())
                 for p in papers]
        try:
            scores = self._score(pairs)
            ranked = sorted(zip(papers, (float(s) for s in scores)),
                            key=lambda it: it[1], reverse=True)
        except Exception as e:
            self.logger.error(f"重排序失敗，改用原順序：{e}")
            ranked = list(candidates)

        return ranked[:k] if k else ranked
