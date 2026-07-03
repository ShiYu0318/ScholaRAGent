"""語意快取：以查詢語意相似度命中，省去重複 LLM 呼叫。

不同於字串完全比對，語意快取用嵌入相似度判斷「問的是不是同一件事」，
措辭略有不同也能命中。以 embedder 內積（向量已正規化）為相似度。
"""
import numpy as np

from src.utils.logger import get_logger


class SemanticCache:
    def __init__(self, embedder, threshold=0.9, max_size=256):
        self.logger = get_logger(self.__class__.__name__)
        self.embedder = embedder
        self.threshold = threshold
        self.max_size = max_size
        self._keys = []      # 快取查詢的嵌入
        self._values = []    # 對應的答案

    def put(self, query, value):
        vec = self.embedder.encode([query])[0]
        self._keys.append(vec)
        self._values.append(value)
        if len(self._values) > self.max_size:   # 簡單 FIFO 汰換
            self._keys.pop(0)
            self._values.pop(0)

    def get(self, query):
        """回傳最相似且超過門檻的快取答案；無則 None。"""
        if not self._values:
            return None
        q = self.embedder.encode([query])[0]
        sims = np.asarray(self._keys) @ q
        i = int(np.argmax(sims))
        if sims[i] >= self.threshold:
            self.logger.info(f"語意快取命中（sim={sims[i]:.3f}）")
            return self._values[i]
        return None
