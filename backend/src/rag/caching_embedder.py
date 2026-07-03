"""嵌入快取：包一層 embedder，重複文字不重算，省時省成本。

介面與 Embedder 相同（`encode(list[str]) -> ndarray`、`dim`），可直接替換注入。
"""
import numpy as np

from src.utils.logger import get_logger


class CachingEmbedder:
    def __init__(self, embedder, max_size=4096):
        self.logger = get_logger(self.__class__.__name__)
        self.embedder = embedder
        self.dim = embedder.dim
        self.max_size = max_size
        self._cache = {}

    def encode(self, texts):
        texts = list(texts)
        missing = [t for t in texts if t not in self._cache]
        if missing:
            # 只對未快取者計算，保持原順序去重
            uniq = list(dict.fromkeys(missing))
            vecs = self.embedder.encode(uniq)
            for t, v in zip(uniq, vecs):
                self._cache[t] = np.asarray(v)
            if len(self._cache) > self.max_size:            # 簡單汰換
                for k in list(self._cache)[: len(self._cache) - self.max_size]:
                    self._cache.pop(k, None)
        return np.asarray([self._cache[t] for t in texts], dtype="float32")
