"""Corrective RAG。

當本地檢索的最高信心分數過低（可能收錄不足），就觸發外部搜尋（實務上接
ArxivCrawler.search_topic）抓新論文補證據，再與本地結果融合。避免「庫裡沒有
就硬答」造成幻覺。`fallback_search(query) -> [paper]` 可注入，離線可測。
"""
from src.utils.logger import get_logger

_logger = get_logger("corrective_rag")


def corrective_retrieve(query, primary_hits, fallback_search, min_score=0.3, k=4):
    """回傳 (results[(paper, score)], corrected: bool)。

    primary_hits 最高分 >= min_score 視為有信心，直接回傳；否則以外部搜尋補充。
    """
    top = primary_hits[0][1] if primary_hits else 0.0
    if top >= min_score:
        return primary_hits[:k], False

    _logger.info(f"檢索信心不足（top={top:.3f} < {min_score}），觸發外部補充")
    merged = list(primary_hits)
    seen = {p["id"] for p, _ in primary_hits}
    for paper in fallback_search(query):
        if paper["id"] not in seen:
            seen.add(paper["id"])
            merged.append((paper, 0.0))     # 外部補充項，分數未知
    return merged[:k], True
