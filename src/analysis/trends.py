"""關鍵字時序趨勢分析與簡單預測（Week13）。

從論文集合抽取關鍵字、依時間分桶統計，並用移動平均 / 線性趨勢預測
下一期熱度。先以輕量統計方法起步（資料量足夠時再換 LSTM）。
"""
import re
from collections import Counter, defaultdict

import numpy as np

# 常見英文停用詞 + 論文摘要常見無資訊詞
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "by",
    "we", "our", "is", "are", "be", "this", "that", "these", "those", "it", "its",
    "as", "at", "from", "can", "which", "such", "using", "use", "used", "based",
    "propose", "proposed", "method", "methods", "approach", "results", "result",
    "paper", "model", "models", "show", "shows", "novel", "new", "via", "than",
    "more", "most", "also", "into", "between", "over", "under", "not", "but",
    "their", "they", "them", "has", "have", "had", "was", "were", "been", "will",
}
_WORD = re.compile(r"[a-zA-Z][a-zA-Z0-9\-]{2,}")


def _tokens(text):
    return [w.lower() for w in _WORD.findall(text or "")
            if w.lower() not in _STOPWORDS]


def _bucket(published, granularity="month"):
    """把 'YYYY-MM-DD' 轉成時間桶鍵。"""
    if not published or len(published) < 7:
        return None
    return published[:7] if granularity == "month" else published[:4]


def extract_keywords(papers, top_n=20):
    """回傳 [(keyword, count)]，依出現次數排序。"""
    counter = Counter()
    for p in papers:
        counter.update(set(_tokens(f"{p.get('title', '')} {p.get('abstract', '')}")))
    return counter.most_common(top_n)


def keyword_timeseries(papers, keyword, granularity="month"):
    """回傳 (periods, counts)：某關鍵字隨時間桶出現的論文數（依時間排序）。"""
    keyword = keyword.lower()
    per_bucket = defaultdict(int)
    for p in papers:
        bucket = _bucket(p.get("published", ""), granularity)
        if bucket is None:
            continue
        if keyword in set(_tokens(f"{p.get('title', '')} {p.get('abstract', '')}")):
            per_bucket[bucket] += 1
    periods = sorted(per_bucket)
    return periods, [per_bucket[b] for b in periods]


def forecast(counts, method="moving_average", window=3):
    """由歷史計數預測下一期數值（非負）。

    - moving_average：取最後 window 期平均。
    - linear：對序列做最小平方線性擬合並外推一期。
    """
    counts = [float(c) for c in counts]
    if not counts:
        return 0.0
    if method == "linear" and len(counts) >= 2:
        x = np.arange(len(counts))
        slope, intercept = np.polyfit(x, counts, 1)
        return float(max(0.0, slope * len(counts) + intercept))
    tail = counts[-window:] if window > 0 else counts
    return float(sum(tail) / len(tail))


def trending_keywords(papers, top_n=10, granularity="month"):
    """找出「上升中」的關鍵字：以時序線性斜率排序，回傳 [(keyword, slope)]。

    只考慮至少橫跨兩個時間桶、且總出現數達門檻的關鍵字。
    """
    candidates = [kw for kw, cnt in extract_keywords(papers, top_n=80) if cnt >= 2]
    scored = []
    for kw in candidates:
        periods, counts = keyword_timeseries(papers, kw, granularity)
        if len(counts) < 2:
            continue
        x = np.arange(len(counts))
        slope = float(np.polyfit(x, counts, 1)[0])
        if slope > 0:
            scored.append((kw, slope))
    scored.sort(key=lambda it: it[1], reverse=True)
    return scored[:top_n]
