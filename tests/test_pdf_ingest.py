"""PDF 全文攝取，離線用 PyMuPDF 自建 PDF。"""
import fitz  # PyMuPDF

from src.rag.pdf_ingest import extract_text, split_sections, fetch_and_ingest


def _make_pdf(lines):
    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for line in lines:
        page.insert_text((72, y), line)
        y += 18
    return doc.tobytes()


def test_extract_text_from_pdf():
    pdf = _make_pdf(["Hello World", "second line here"])
    text = extract_text(pdf)
    assert "Hello World" in text
    assert "second line" in text


def test_split_sections_by_numbered_headings():
    text = "1 Introduction\nintro body text\n2 Method\nmethod body text"
    secs = split_sections(text)
    heads = [h for h, _ in secs]
    assert "1 Introduction" in heads and "2 Method" in heads
    intro = dict(secs)["1 Introduction"]
    assert "intro body text" in intro


def test_split_sections_recognizes_plain_headings():
    text = "Abstract\nwe present...\nConclusion\nwe conclude"
    heads = [h for h, _ in split_sections(text)]
    assert "Abstract" in heads and "Conclusion" in heads


def test_fetch_and_ingest_returns_sections_via_injected_fetch():
    pdf = _make_pdf(["1 Introduction", "hello intro"])
    got = fetch_and_ingest("2310.06825", fetch=lambda url: pdf)
    assert any("Introduction" in h for h, _ in got)
