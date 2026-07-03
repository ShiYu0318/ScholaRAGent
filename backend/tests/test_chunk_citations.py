"""片段級 [REF:chunk_id] 引用。"""
from src.rag.chunk_citations import (
    format_context, extract_refs, resolve_refs, render_sources,
)


def _chunks():
    return [
        {"id": "c1", "text": "attention improves x", "paper_title": "Paper A",
         "section": "Method", "link": "http://a"},
        {"id": "c2", "text": "gnn models y", "paper_title": "Paper B",
         "section": "Results", "link": "http://b"},
    ]


def test_format_context_labels_each_chunk():
    out = format_context(_chunks())
    assert "[REF:c1] attention improves x" in out
    assert "[REF:c2] gnn models y" in out


def test_extract_refs_in_order_deduped():
    assert extract_refs("a [REF:c1] b [REF:c2] c [REF:c1]") == ["c1", "c2"]


def test_extract_refs_none():
    assert extract_refs("no refs here") == []


def test_resolve_refs_maps_to_source_metadata():
    used = resolve_refs("claim [REF:c2] supported", _chunks())
    assert len(used) == 1
    assert used[0]["paper_title"] == "Paper B"
    assert used[0]["section"] == "Results"


def test_resolve_ignores_unknown_ref():
    assert resolve_refs("see [REF:zzz]", _chunks()) == []


def test_render_sources_block():
    block = render_sources("uses [REF:c1] and [REF:c2]", _chunks())
    assert "c1" in block and "Paper A" in block and "Method" in block
    assert "http://b" in block


def test_render_sources_empty_when_no_refs():
    assert render_sources("no citations", _chunks()) == ""
