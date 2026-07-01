"""Obsidian 知識庫匯出。"""
from src.tools.obsidian_export import to_obsidian


def _p(pid, title, **kw):
    base = {"id": pid, "title": title, "authors": "A. Author",
            "published": "2023-05-01", "abstract": f"Abstract of {title}."}
    base.update(kw)
    return base


def test_produces_one_note_per_paper():
    out = to_obsidian([_p("1", "Paper A"), _p("2", "Paper B")])
    assert len(out) == 2
    assert any(name.endswith(".md") for name in out)


def test_note_has_frontmatter_and_abstract():
    out = to_obsidian([_p("1", "Paper A", abstract="key idea here")])
    content = out["Paper A.md"]
    assert content.startswith("---")          # YAML frontmatter
    assert "year: 2023" in content
    assert "key idea here" in content


def test_edges_become_wikilinks():
    out = to_obsidian([_p("1", "Paper A"), _p("2", "Paper B")], edges=[("1", "2")])
    assert "[[Paper B]]" in out["Paper A.md"]   # 有向連結指向被引


def test_sanitizes_illegal_filename_chars():
    out = to_obsidian([_p("1", "A/B: C?")])
    assert all("/" not in name.replace(".md", "") for name in out)


def test_empty_returns_empty():
    assert to_obsidian([]) == {}
