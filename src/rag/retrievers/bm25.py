"""輕量 BM25 稀疏檢索（純 Python，無外部依賴）。

用於與稠密向量檢索做混合。對關鍵字/專有名詞（模型名、資料集名）特別有效，
補足純語意檢索容易漏掉精確詞的問題。
"""
import math
import re
from collections import Counter

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokenize(text):
    return _TOKEN.findall((text or "").lower())


class BM25Index:
    def __init__(self, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.papers = []
        self.docs = []          # 每篇的 token 清單
        self.idf = {}
        self.avgdl = 0.0

    def fit(self, papers, text_fn=None):
        """以論文集合建索引。text_fn 決定用哪些欄位組成文件（預設 title + abstract）。"""
        text_fn = text_fn or (lambda p: f"{p.get('title', '')} {p.get('abstract', '')}")
        self.papers = list(papers)
        self.docs = [_tokenize(text_fn(p)) for p in self.papers]

        df = Counter()
        for doc in self.docs:
            for term in set(doc):
                df[term] += 1
        n = len(self.docs) or 1
        # BM25 的 idf（加 1 平滑避免負值）
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        self.avgdl = (sum(len(d) for d in self.docs) / len(self.docs)) if self.docs else 0.0
        return self

    def _score(self, query_tokens, doc):
        freqs = Counter(doc)
        dl = len(doc)
        score = 0.0
        for term in query_tokens:
            f = freqs.get(term, 0)
            if not f:
                continue
            idf = self.idf.get(term, 0.0)
            denom = f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
            score += idf * (f * (self.k1 + 1)) / denom
        return score

    def search(self, query, k=10):
        """回傳 [(paper, score)]，分數 > 0，依分數排序。"""
        q = _tokenize(query)
        scored = [(self.papers[i], self._score(q, doc)) for i, doc in enumerate(self.docs)]
        scored = [(p, s) for p, s in scored if s > 0]
        scored.sort(key=lambda it: it[1], reverse=True)
        return scored[:k]
