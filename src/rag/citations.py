"""答案引用標註。

把檢索到的論文整理成可稽核的編號來源清單，供 LLM 以 [n] 標註出處、
使用者點回原文，降低幻覺、提升可信度。
"""


def format_citations(papers):
    """回傳編號來源區塊（Markdown）；空清單回傳空字串。

    每行：`[n] 標題 — 連結 (id)`
    """
    if not papers:
        return ""
    lines = [" **來源**"]
    for i, p in enumerate(papers, 1):
        title = p.get("title", "(無標題)")
        link = p.get("link", "")
        pid = p.get("id", "")
        tail = f" — {link}" if link else ""
        tag = f" ({pid})" if pid else ""
        lines.append(f"[{i}] {title}{tail}{tag}")
    return "\n".join(lines)
