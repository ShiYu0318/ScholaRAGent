"""Self-RAG 充分性反思。

生成答案前，先讓 LLM 檢視「目前檢索到的脈絡是否足以回答問題」。
不足時要求它給出一個更好的檢索查詢，交回檢索迴圈再補證據（上限 N 輪）。
與  組合即成 Self-RAG：檢索->反思->（必要時）再檢索->作答。
"""
from src.utils.logger import get_logger

_logger = get_logger("self_rag")

_SYSTEM = (
    "你是嚴謹的研究審查者。判斷下列脈絡是否足以充分回答問題。"
    "若足夠，只輸出 YES。若不足，輸出 `NO: <一個更好的英文檢索查詢>`。"
    "不要多餘說明。"
)


def assess_sufficiency(question, contexts, llm):
    """回傳 (sufficient: bool, refine_query: str | None)。

    LLM 失敗時預設 sufficient=True，避免無限重試。
    """
    joined = "\n---\n".join(contexts)
    user = f"問題：{question}\n\n脈絡：\n{joined}"
    try:
        reply = (llm._chat(_SYSTEM, user, max_tokens=60) or "").strip()
    except Exception as e:
        _logger.error(f"充分性判斷失敗，視為足夠：{e}")
        return True, None

    if reply.upper().startswith("YES"):
        return True, None
    # 不足：嘗試解析 "NO: <query>"
    refine = None
    if ":" in reply or "：" in reply:
        refine = reply.split("：", 1)[-1].split(":", 1)[-1].strip() or None
    return False, refine
