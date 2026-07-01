"""查詢路由 local / global（GraphRAG / C10，受 meetGRAG 啟發）。

- local：針對特定實體／論文的問題 → 向量檢索 + 圖鄰域擴展（[graph_rag].graph_context）。
- global：宏觀、跨文件的問題（「這領域整體在做什麼」）→ 社群報告推理（[C11] global_search）。

有 LLM 就用 LLM 分類；無 LLM 或失敗／回覆無效則退回關鍵字啟發式。
"""
from src.utils.logger import get_logger

_logger = get_logger("router")

# 宏觀問題的訊號詞（中英）
_GLOBAL_HINTS = (
    "overview", "landscape", "overall", "trend", "trends", "across", "in general",
    "state of", "big picture", "summarize the field", "whole field",
    "整體", "趨勢", "全貌", "研究地圖", "宏觀", "整個領域", "總覽",
)

_SYSTEM = (
    "判斷這個問題屬於 local 還是 global：local 是關於特定論文/方法/實體的具體問題；"
    "global 是關於整個研究領域的宏觀、跨文件問題。只輸出 local 或 global。"
)


def _heuristic(query):
    q = (query or "").lower()
    return "global" if any(h in q for h in _GLOBAL_HINTS) else "local"


def route_query(query, llm=None):
    """回傳 'local' 或 'global'。"""
    if llm is not None:
        try:
            reply = (llm._chat(_SYSTEM, query, max_tokens=8) or "").strip().lower()
            if "global" in reply:
                return "global"
            if "local" in reply:
                return "local"
        except Exception as e:
            _logger.info(f"路由 LLM 失敗，改用啟發式：{e}")
    return _heuristic(query)
