"""互動驅動的推薦排序（Week14 輕量 RLHF 概念）。

以使用者互動訊號（點擊/按讚/訂閱/評分…的加權總分）與新鮮度，
線性組合成排序分數，動態調整論文推薦順序。權重可調，之後可由
互動回饋自動學習（reward = 正向互動）。
"""
from datetime import date

# 各互動類型的預設獎勵權重（可由設定或學習調整）
DEFAULT_ACTION_WEIGHTS = {
    "click": 1.0,
    "like": 3.0,
    "subscribe": 5.0,
    "share": 4.0,
    "rate": 2.0,
    "ask": 1.5,
    "dwell": 0.5,
}


def _recency_score(published, today=None):
    """越新的論文分數越高（0~1），以 30 天為衰減尺度。"""
    if not published or len(published) < 10:
        return 0.0
    try:
        y, m, d = (int(x) for x in published[:10].split("-"))
        age_days = ((today or date.today()) - date(y, m, d)).days
    except (ValueError, TypeError):
        return 0.0
    if age_days < 0:
        age_days = 0
    return 1.0 / (1.0 + age_days / 30.0)


def rank_papers(papers, interaction_counts=None, w_interaction=1.0, w_recency=1.0, today=None):
    """回傳依綜合分數由高到低排序的論文清單（不改動原輸入）。

    - interaction_counts：{paper_id: 加權互動總分}（來自 Database.interaction_counts）。
    - w_interaction / w_recency：兩項訊號的權重。
    """
    interaction_counts = interaction_counts or {}
    scored = []
    for p in papers:
        inter = float(interaction_counts.get(p.get("id"), 0.0))
        recency = _recency_score(p.get("published", ""), today=today)
        score = w_interaction * inter + w_recency * recency
        scored.append((score, p))
    # 穩定排序：分數相同時維持原順序
    scored.sort(key=lambda it: it[0], reverse=True)
    return [p for _, p in scored]


def weighted_interaction_score(action_counts, weights=None):
    """把 {action: 次數} 依權重換算成單一 reward 分數。"""
    weights = weights or DEFAULT_ACTION_WEIGHTS
    return sum(weights.get(a, 1.0) * n for a, n in (action_counts or {}).items())
