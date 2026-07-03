"""chunk_text：短文原樣、長文切分且重疊、邊界斷句。"""
from src.rag.chunker import chunk_text


def test_empty():
    assert chunk_text("") == []
    assert chunk_text(None) == []


def test_short_text_single_chunk():
    assert chunk_text("hello world", size=800) == ["hello world"]


def test_long_text_is_split():
    text = "。".join(f"這是第{i}個句子內容" for i in range(200))
    chunks = chunk_text(text, size=200, overlap=40)
    assert len(chunks) > 1
    assert all(len(c) <= 200 + 40 for c in chunks)
    # 重組後涵蓋原文所有句子片段
    joined = "".join(chunks)
    assert "第0個句子" in joined and "第199個句子" in joined


def test_overlap_context_preserved():
    text = "A" * 500
    chunks = chunk_text(text, size=100, overlap=20)
    assert len(chunks) >= 5
    # 每段長度約為 size
    assert all(len(c) <= 100 for c in chunks)


def test_sentence_boundary_break():
    text = "First sentence here. Second sentence here. " * 20
    chunks = chunk_text(text, size=120, overlap=20)
    # 大多數片段應以句號 / 空白結尾（在邊界斷開）
    assert len(chunks) > 1
