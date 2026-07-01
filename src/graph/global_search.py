"""全域搜尋（GraphRAG / C11，受 meetGRAG / GraphRAG 啟發）。

回答宏觀、跨文件的問題時，不做單點檢索，而是對每個研究社群摘要（[C3]
summarize_communities）先各自產生部分答案（map），再彙整成最終答案（reduce）。
與 [C10] router 搭配：global 問題走這裡，local 問題走向量+圖檢索。
"""
from src.utils.logger import get_logger

_logger = get_logger("global_search")

_MAP_SYSTEM = (
    "根據這個研究社群的摘要，針對使用者問題給出相關的部分回答；"
    "若此社群與問題無關，回覆『無關』。簡潔。"
)
_REDUCE_SYSTEM = (
    "綜合以下各研究社群的部分回答，寫出對使用者問題的完整、宏觀回答，"
    "指出主要方向、共識與分歧。繁體中文。"
)


def global_search(query, communities, llm, max_communities=10):
    """對社群摘要做 map-reduce，回傳最終答案。"""
    if not communities:
        return "（目前沒有可用的研究社群摘要，無法進行全域搜尋。）"

    partials = []
    for c in communities[:max_communities]:
        user = f"問題：{query}\n\n社群摘要：{c.get('summary', '')}"
        try:
            ans = (llm._chat(_MAP_SYSTEM, user, max_tokens=250) or "").strip()
        except Exception as e:
            _logger.error(f"map 階段失敗：{e}")
            continue
        if ans and "無關" not in ans:
            partials.append(ans)

    joined = "\n\n".join(f"- {p}" for p in partials)
    try:
        return llm._chat(_REDUCE_SYSTEM, f"問題：{query}\n\n各社群部分回答：\n{joined}",
                         max_tokens=700)
    except Exception as e:
        _logger.error(f"reduce 階段失敗：{e}")
        return joined or "（全域搜尋失敗）"
