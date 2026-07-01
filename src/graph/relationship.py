"""論文關係分析。

用 LLM 判斷兩篇論文的關係（延伸/比較/反駁/應用…）並給一句說明，
可標在引用圖的邊上，讓使用者一眼看懂「這兩篇怎麼關聯」。離線 stub 可測。
"""
from src.utils.logger import get_logger

_logger = get_logger("relationship")

KNOWN_RELATIONS = {
    "extends", "builds_on", "compares", "contradicts", "applies", "uses", "unrelated",
}

_SYSTEM = (
    "判斷論文 B 相對於論文 A 的關係，從 "
    "[extends, builds_on, compares, contradicts, applies, uses, unrelated] 選一個，"
    "輸出格式嚴格為 `<relation>: <一句說明>`。只輸出這一行。"
)


def analyze_relationship(paper_a, paper_b, llm):
    """回傳 {relation, explanation}。無法解析->related；LLM 出錯->unknown。"""
    user = (f"A 標題：{paper_a.get('title', '')}\nA 摘要：{paper_a.get('abstract', '')}\n\n"
            f"B 標題：{paper_b.get('title', '')}\nB 摘要：{paper_b.get('abstract', '')}")
    try:
        reply = (llm._chat(_SYSTEM, user, max_tokens=120) or "").strip()
    except Exception as e:
        _logger.error(f"關係分析失敗：{e}")
        return {"relation": "unknown", "explanation": ""}

    if ":" in reply or "：" in reply:
        left, right = reply.replace("：", ":").split(":", 1)
        rel = left.strip().lower().replace(" ", "_").replace("-", "_")
        if rel in KNOWN_RELATIONS:
            return {"relation": rel, "explanation": right.strip()}
        return {"relation": "related", "explanation": reply}
    return {"relation": "unknown", "explanation": reply}
