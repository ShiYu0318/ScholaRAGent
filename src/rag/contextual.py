"""Contextual chunk embedding（Advanced RAG / A7）。

參考 Anthropic「Contextual Retrieval」：嵌入前，先讓 LLM 針對整篇文件替每個
片段補一句「定位說明」（本片段在全文的角色），再與原片段一起嵌入。
如此可補回被切碎後遺失的上下文，明顯提升召回。失敗時退回原片段。
"""
from src.utils.logger import get_logger

_logger = get_logger("contextual")

_SYSTEM = (
    "你會看到一份文件與其中一個片段。請用一句話說明這個片段在整份文件中的定位／主題，"
    "供檢索用。只輸出這句話，不要多餘說明。"
)


def contextualize_chunk(document, chunk, llm):
    """回傳「定位句\\n\\n原片段」；LLM 失敗或空輸出時退回原片段。"""
    try:
        user = f"<document>\n{document}\n</document>\n<chunk>\n{chunk}\n</chunk>"
        ctx = (llm._chat(_SYSTEM, user, max_tokens=80) or "").strip()
        return f"{ctx}\n\n{chunk}" if ctx else chunk
    except Exception as e:
        _logger.error(f"contextualize 失敗，改用原片段：{e}")
        return chunk


def contextualize_all(document, chunks, llm):
    return [contextualize_chunk(document, ch, llm) for ch in chunks]
