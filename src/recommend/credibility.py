"""可信度／影響力訊號（Recommend / D9）。

用 [OpenAlex] 的被引數替論文標記影響力分級，幫使用者快速判斷「這篇值不值得
細讀」。純以被引數分級（後續可再結合 venue、作者 h-index、是否被反駁）。
client 需具 `work_by_arxiv(arxiv_id, title=None)`，離線用 stub 測。
"""
from src.utils.logger import get_logger

_logger = get_logger("credibility")

_HIGH, _MED = 100, 10


def _tier(cites):
    if cites >= _HIGH:
        return "high"
    if cites >= _MED:
        return "medium"
    return "low"


def credibility_signal(paper, client):
    """回傳 {cited_by_count, tier}；查不到視為 0（low）。"""
    work = client.work_by_arxiv(paper.get("id"), title=paper.get("title"))
    cites = work["cited_by_count"] if work else 0
    return {"cited_by_count": cites, "tier": _tier(cites)}


def annotate_credibility(papers, client):
    """就地替每篇論文加上 credibility 欄位並回傳。"""
    for p in papers:
        p["credibility"] = credibility_signal(p, client)
    return papers


def format_signal(sig):
    """人類可讀的一行標記。"""
    emoji = {"high": "🔥 高影響", "medium": "📈 中等", "low": "🌱 新／少被引"}
    return f"{emoji.get(sig['tier'], '')}（被引 {sig['cited_by_count']}）"
