"""PDF 全文攝取（Advanced RAG / D1）。

只靠摘要不夠深入——這裡用 PyMuPDF 解析 arXiv PDF，抽出全文並依常見章節標題
切段，供問答／摘要吃到方法、實驗等細節。`fetch` 可注入，離線用自建 PDF 測試；
預設用 requests 抓 arXiv PDF。（GROBID 可作更精準的替代，但需 Docker。）
"""
import re

import fitz  # PyMuPDF

from src.utils.logger import get_logger

_logger = get_logger("pdf_ingest")

# 標題須佔滿整行（避免把以章節字詞開頭的內文誤判為標題）
_HEADING = re.compile(
    r"^(?:\d+(?:\.\d+)*\.?\s+)?"
    r"(abstract|introduction|related work|background|method(?:s|ology)?|approach|"
    r"experiments?|evaluation|results?|analysis|discussion|conclusions?|references)"
    r"\s*$",
    re.IGNORECASE,
)


def extract_text(pdf_bytes):
    """抽出 PDF 全文（各頁以換行相接）。"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        return "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()


def split_sections(text):
    """依章節標題把全文切成 [(heading, body)]。"""
    sections, head, buf = [], "_preamble", []
    for line in text.splitlines():
        s = line.strip()
        if s and len(s) < 60 and _HEADING.match(s):
            if buf:
                sections.append((head, "\n".join(buf).strip()))
            head, buf = s, []
        else:
            buf.append(line)
    if buf:
        sections.append((head, "\n".join(buf).strip()))
    return [(h, b) for h, b in sections if b or h != "_preamble"]


def _default_fetch(url):
    import requests
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.content


def fetch_and_ingest(arxiv_id, fetch=None):
    """抓 arXiv PDF 並回傳章節清單 [(heading, body)]；失敗回空清單。"""
    fetch = fetch or _default_fetch
    clean = re.sub(r"v\d+$", "", (arxiv_id or "").strip())
    url = f"https://arxiv.org/pdf/{clean}"
    try:
        pdf = fetch(url)
        return split_sections(extract_text(pdf))
    except Exception as e:
        _logger.error(f"PDF 攝取失敗（{clean}）：{e}")
        return []
