"""可重現性訊號：從論文 metadata 抽 code 連結，離線純函式。"""
from src.recommend.reproducibility import extract_code_links, reproducibility_signal


def test_extracts_github_link_from_abstract():
    p = {"abstract": "We release code at https://github.com/foo/bar-baz for reproduction."}
    assert extract_code_links(p) == ["https://github.com/foo/bar-baz"]


def test_extracts_from_comment_field_and_dedupes():
    p = {"abstract": "see github.com/a/b", "comment": "code: https://github.com/a/b"}
    assert extract_code_links(p) == ["https://github.com/a/b"]


def test_supports_gitlab():
    p = {"abstract": "https://gitlab.com/group/proj"}
    assert "https://gitlab.com/group/proj" in extract_code_links(p)


def test_no_links_returns_empty():
    assert extract_code_links({"abstract": "no code available"}) == []


def test_reproducibility_signal_flags_code():
    sig = reproducibility_signal({"abstract": "code https://github.com/a/b"})
    assert sig["has_code"] is True
    assert sig["repos"] == ["https://github.com/a/b"]


def test_reproducibility_signal_no_code():
    sig = reproducibility_signal({"abstract": "nothing"})
    assert sig["has_code"] is False and sig["repos"] == []
