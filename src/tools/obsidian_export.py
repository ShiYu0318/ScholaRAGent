"""Obsidian 知識庫匯出（Tools / C9，受 paper_master 啟發）。

把論文與其關聯匯成一組 Obsidian Markdown 筆記：YAML frontmatter（供 Dataview
查詢）＋ `[[wikilinks]]`（供 Juggl 圖譜）。研究者可直接把這些 .md 丟進 vault，
在 Obsidian 裡瀏覽論文知識圖、做筆記。純函式、離線可測。
"""
import re

_ILLEGAL = re.compile(r'[\\/:*?"<>|#^\[\]]+')


def _note_name(title):
    return _ILLEGAL.sub(" ", title or "").strip() or "untitled"


def _paper_note(paper, related_titles):
    title = paper.get("title", "")
    year = (paper.get("published", "") or "")[:4]
    tags = paper.get("tags", ["paper"])
    fm = [
        "---",
        f'id: "{paper.get("id", "")}"',
        f'title: "{title}"',
        f'authors: "{paper.get("authors", "")}"',
        f"year: {year}" if year else "year:",
        f"tags: [{', '.join(tags)}]",
    ]
    if "credibility" in paper:
        fm.append(f"cited_by: {paper['credibility'].get('cited_by_count', 0)}")
    fm.append("---")

    body = [f"# {title}", "", paper.get("abstract", "")]
    if paper.get("link"):
        body += ["", f"[arXiv]({paper['link']})"]
    if related_titles:
        body += ["", "## 相關"]
        body += [f"- [[{t}]]" for t in related_titles]
    return "\n".join(fm) + "\n\n" + "\n".join(body) + "\n"


def to_obsidian(papers, edges=None):
    """回傳 {filename.md: content}。edges 為 [(src_id, dst_id)]（有向連結）。"""
    if not papers:
        return {}
    by_id = {p["id"]: p for p in papers}
    links = {}       # src_id -> [dst note name]（去重）
    for src, dst in (edges or []):
        if src in by_id and dst in by_id:
            name = _note_name(by_id[dst]["title"])
            links.setdefault(src, [])
            if name not in links[src]:
                links[src].append(name)

    notes = {}
    for p in papers:
        fname = f"{_note_name(p.get('title', ''))}.md"
        notes[fname] = _paper_note(p, links.get(p["id"], []))
    return notes
