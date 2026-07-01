"""片段級引用 [REF:chunk_id]（Advanced RAG / A8，受 meetGRAG 啟發）。

把 A5 的論文層引用升級到**片段層**：檢索脈絡中每個 chunk 標上 `[REF:id]`，
請 LLM 於句末引用對應 id；事後解析答案裡的 `[REF:id]`，對應回精確來源
（論文、章節、連結），做到可點回原文的細粒度追溯。
"""
import re

_REF = re.compile(r"\[REF:([^\]]+)\]")


def format_context(chunks):
    """把 chunks 串成帶 [REF:id] 標籤的脈絡文字。"""
    return "\n".join(f"[REF:{c['id']}] {c.get('text', '')}" for c in chunks)


def extract_refs(answer):
    """依出現順序取出答案中引用的 chunk id（去重）。"""
    seen, out = set(), []
    for m in _REF.finditer(answer or ""):
        cid = m.group(1).strip()
        if cid not in seen:
            seen.add(cid)
            out.append(cid)
    return out


def resolve_refs(answer, chunks):
    """回傳答案實際引用到的來源 metadata 清單（依引用順序）。"""
    by_id = {c["id"]: c for c in chunks}
    return [by_id[cid] for cid in extract_refs(answer) if cid in by_id]


def render_sources(answer, chunks):
    """把答案引用到的來源整理成可稽核區塊；沒有引用回空字串。"""
    used = resolve_refs(answer, chunks)
    if not used:
        return ""
    lines = ["📚 **來源**"]
    for c in used:
        title = c.get("paper_title", "")
        section = c.get("section", "")
        link = c.get("link", "")
        loc = f" · {section}" if section else ""
        tail = f" — {link}" if link else ""
        lines.append(f"[{c['id']}] {title}{loc}{tail}")
    return "\n".join(lines)
