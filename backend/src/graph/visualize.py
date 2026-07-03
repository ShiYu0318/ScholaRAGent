"""概念圖視覺化匯出。

把概念圖輸出成 Mermaid 圖（純文字、可貼進 Markdown/Discord/前端渲染），
讓使用者一眼看到研究領域全貌與論文脈絡。Mermaid 免依賴、離線可測。
"""
import re

_ID = re.compile(r"[^0-9A-Za-z]+")


def _node_id(name, seen):
    """把節點名轉成安全的 Mermaid id（英數 + 底線），確保唯一。"""
    base = _ID.sub("_", name).strip("_") or "n"
    nid = base
    i = 1
    while nid in seen and seen[nid] != name:
        i += 1
        nid = f"{base}_{i}"
    seen[nid] = name
    return nid


def to_mermaid(graph, max_edges=200):
    """回傳 Mermaid `graph LR` 字串。標籤保留原文、id 消毒。"""
    lines = ["graph LR"]
    seen = {}
    ids = {}
    for i, (u, v, d) in enumerate(graph.edges(data=True)):
        if i >= max_edges:
            break
        uid = ids.setdefault(u, _node_id(u, seen))
        vid = ids.setdefault(v, _node_id(v, seen))
        rel = d.get("relation", "")
        edge = f'  {uid}["{u}"] -->|{rel}| {vid}["{v}"]' if rel \
            else f'  {uid}["{u}"] --> {vid}["{v}"]'
        lines.append(edge)
    return "\n".join(lines)
