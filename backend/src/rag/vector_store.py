"""FAISS 向量庫：建庫、持久化、相似度檢索，並保存論文 metadata。"""
import json
import re

import faiss

from src import config
from src.rag.embedder import Embedder
from src.utils.logger import get_logger

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokenize(text):
    """英數斷詞（小寫）；用於輕量詞彙 rerank，中文以整串比對即可。"""
    return set(_TOKEN.findall((text or "").lower()))


def _lexical_overlap(query_tokens, doc_text):
    """query 與文件的詞彙重疊比例（Jaccard），回傳 0~1。"""
    doc_tokens = _tokenize(doc_text)
    if not query_tokens or not doc_tokens:
        return 0.0
    return len(query_tokens & doc_tokens) / len(query_tokens | doc_tokens)


class VectorStore:
    def __init__(self, embedder=None, index_type=None, hnsw_m=None):
        self.logger = get_logger(self.__class__.__name__)
        self.embedder = embedder or Embedder()
        self.index_type = index_type or config.INDEX_TYPE
        self.hnsw_m = hnsw_m or config.HNSW_M
        self.index = self._new_index(self.embedder.dim)
        self.papers = []          # 與 index 向量一一對應的論文 metadata
        self._ids = set()         # 已收錄的 arxiv id，用於去重
        self.load()

    def _new_index(self, dim):
        """建立向量索引：flat=精確暴力搜尋；hnsw=近似最近鄰（大量論文更快）。"""
        if self.index_type == "hnsw":
            return faiss.IndexHNSWFlat(dim, self.hnsw_m, faiss.METRIC_INNER_PRODUCT)
        return faiss.IndexFlatIP(dim)

    def add(self, papers):
        """加入新論文（依 arxiv id 去重），回傳實際新增的清單。"""
        new = [p for p in papers if p["id"] not in self._ids]
        if not new:
            self.logger.info("沒有新論文需要加入向量庫")
            return []

        texts = [f"{p['title']}. {p['abstract']}" for p in new]
        vectors = self.embedder.encode(texts)
        self.index.add(vectors)
        for p in new:
            self.papers.append(p)
            self._ids.add(p["id"])

        self.logger.info(f"向量庫新增 {len(new)} 篇，現有 {len(self.papers)} 篇")
        self.save()
        return new

    def search(self, query, k=4, where=None, rerank=True):
        """回傳與 query 最相似的論文清單（向後相容：預設回傳論文 dict 清單）。

        - where：可選的過濾函式 `paper -> bool`，例如只留特定來源或日期區間。
        - rerank：結合向量分數與詞彙重疊做二階段排序，提升精準度。
        """
        return [p for p, _ in self.search_scored(query, k=k, where=where, rerank=rerank)]

    def search_scored(self, query, k=4, where=None, rerank=True):
        """同 search，但回傳 [(paper, score)]，分數越高越相關。"""
        if self.index.ntotal == 0:
            return []
        vec = self.embedder.encode([query])
        # 過取候選，供過濾與 rerank 之後再取前 k
        fetch_k = min(self.index.ntotal, max(k * 4, 20))
        scores, idxs = self.index.search(vec, fetch_k)

        cands = []
        for score, i in zip(scores[0], idxs[0]):
            if not (0 <= i < len(self.papers)):
                continue
            paper = self.papers[i]
            if where is not None and not where(paper):
                continue
            cands.append((paper, float(score)))

        if rerank and cands:
            q_tokens = _tokenize(query)
            def _final(item):
                paper, vec_score = item
                doc = f"{paper.get('title', '')} {paper.get('abstract', '')}"
                lex = _lexical_overlap(q_tokens, doc)
                return 0.7 * vec_score + 0.3 * lex
            cands = [(p, _final((p, s))) for p, s in cands]
            cands.sort(key=lambda it: it[1], reverse=True)

        return cands[:k]

    def save(self):
        faiss.write_index(self.index, str(config.INDEX_PATH))
        with open(config.METADATA_PATH, "w", encoding="utf-8") as f:
            json.dump(self.papers, f, ensure_ascii=False, indent=2)

    def load(self):
        if config.INDEX_PATH.exists() and config.METADATA_PATH.exists():
            try:
                saved = faiss.read_index(str(config.INDEX_PATH))
                # 若 embedding 模型換過（維度不同，如 all-MiniLM 384 -> bge-m3 1024），
                # 舊 index 不相容，丟棄並以新維度重建，避免檢索崩潰。
                if saved.d != self.embedder.dim:
                    self.logger.warning(
                        f"向量庫維度不符（存檔 {saved.d} != 模型 {self.embedder.dim}），"
                        "已換 embedding 模型；捨棄舊 index，將以新模型重建。"
                    )
                    return
                self.index = saved
                with open(config.METADATA_PATH, encoding="utf-8") as f:
                    self.papers = json.load(f)
                self._ids = {p["id"] for p in self.papers}
                self.logger.info(f"載入向量庫，現有 {len(self.papers)} 篇論文")
            except Exception as e:
                self.logger.error(f"載入向量庫失敗，將重新建立: {e}")
