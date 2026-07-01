"""父文件回溯檢索（Advanced RAG / A4）：small-to-big。

把每篇文件切成小片段（句子級）分別嵌入檢索——小片段語意更聚焦、召回更準；
命中後回傳其「父文件」（整篇論文），確保生成端拿到足夠上下文。
解決「命中一句但上下文不足」與「整篇太長稀釋語意」的兩難。

用注入的 embedder（與 VectorStore 同介面：`encode(list[str]) -> ndarray`），
離線可用 FakeEmbedder 測試。
"""
import numpy as np

from src.rag.chunker import chunk_text
from src.utils.logger import get_logger


class ParentDocumentRetriever:
    def __init__(self, embedder, child_size=200, child_overlap=40):
        self.logger = get_logger(self.__class__.__name__)
        self.embedder = embedder
        self.child_size = child_size
        self.child_overlap = child_overlap
        self._chunks = []          # 每個子片段的文字
        self._parents = []         # 對應父文件（與 _chunks 同索引）
        self._vecs = None          # 子片段嵌入 (n, dim)

    def index(self, papers):
        """把每篇論文切成子片段並嵌入。"""
        self._chunks, self._parents = [], []
        for p in papers:
            doc = f"{p.get('title', '')}. {p.get('abstract', '')}".strip()
            for ch in chunk_text(doc, size=self.child_size, overlap=self.child_overlap):
                self._chunks.append(ch)
                self._parents.append(p)
        self._vecs = self.embedder.encode(self._chunks) if self._chunks else None
        self.logger.info(f"父文件檢索：{len(papers)} 篇 → {len(self._chunks)} 子片段")
        return self

    def retrieve(self, query, k=4):
        """回傳 [(parent_paper, score)]，依最佳子片段分數去重取前 k。"""
        if self._vecs is None or len(self._chunks) == 0:
            return []
        q = self.embedder.encode([query])[0]
        scores = self._vecs @ q                      # 內積（向量已正規化）

        best = {}                                     # parent id -> (score, paper)
        for score, paper in zip(scores, self._parents):
            pid = paper["id"]
            if pid not in best or score > best[pid][0]:
                best[pid] = (float(score), paper)

        ranked = sorted(best.values(), key=lambda it: it[0], reverse=True)
        return [(paper, score) for score, paper in ranked[:k]]
