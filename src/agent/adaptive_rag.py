"""Adaptive-RAG（Agentic RAG / B6）。

依問題複雜度自適應選擇檢索策略（Jeong et al. 2024 的精神）：
- none：不需檢索（打招呼、常識），直接作答省成本。
- simple：單次檢索即可。
- complex：需多跳/多面向 → 走 [B1 ResearchAgent] 之類的迭代檢索。

有 LLM 就用 LLM 分類；否則以啟發式判斷。與 [C10 router] 互補（那個分 local/global，
這個分檢索深度）。
"""
import re

from src.utils.logger import get_logger

_logger = get_logger("adaptive_rag")

_LEVELS = ("none", "simple", "complex")

_WORD = re.compile(r"[a-z一-鿿]+")
_GREETING = {"hello", "hi", "hey", "thanks", "thank", "hola",
             "你好", "哈囉", "謝謝", "嗨"}
_COMPLEX_HINTS = (" and ", " vs ", "compare", "contrast", "differ", "trade-off",
                  "relationship between", "how does", "why does", "比較", "差異", "關係")

_SYSTEM = (
    "判斷回答這個問題需要的檢索程度，只輸出一個詞："
    "none（不需檢索）、simple（單次檢索）、complex（需多步/多面向檢索）。"
)


def _heuristic(query):
    q = (query or "").lower().strip()
    if not q:
        return "none"
    words = _WORD.findall(q)
    first = words[0] if words else ""
    if first in _GREETING and len(q) < 30:
        return "none"
    if any(h in q for h in _COMPLEX_HINTS):
        return "complex"
    return "simple"


def classify_complexity(query, llm=None):
    """回傳 'none' | 'simple' | 'complex'。"""
    if llm is not None:
        try:
            reply = (llm._chat(_SYSTEM, query, max_tokens=8) or "").strip().lower()
            for level in _LEVELS:
                if level in reply:
                    return level
        except Exception as e:
            _logger.info(f"複雜度分類 LLM 失敗，改用啟發式：{e}")
    return _heuristic(query)


def adaptive_retrieve(query, simple_retrieve, multi_retrieve, llm=None):
    """依複雜度分派：none→[]、simple→單次、complex→多步檢索。回傳論文清單。"""
    level = classify_complexity(query, llm=llm)
    if level == "none":
        return []
    if level == "complex":
        return multi_retrieve(query)
    return simple_retrieve(query)
