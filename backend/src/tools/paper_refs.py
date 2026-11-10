"""把使用者貼上的文字辨識成論文識別碼（arXiv ID / arXiv 連結 / DOI）。

純函式、不打網路。回傳 ("arxiv", id)、("doi", doi) 或 None。
"""
import re

_ARXIV_NEW = r"\d{4}\.\d{4,5}(?:v\d+)?"
_ARXIV_OLD = r"[a-z][a-z\-]*(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?"
_ARXIV_ID = re.compile(rf"^(?:{_ARXIV_NEW}|{_ARXIV_OLD})$")
_ARXIV_URL = re.compile(
    rf"arxiv\.org/(?:abs|pdf|html)/({_ARXIV_NEW}|{_ARXIV_OLD})", re.IGNORECASE)
_ARXIV_DOI = re.compile(rf"^10\.48550/arxiv\.({_ARXIV_NEW}|{_ARXIV_OLD})$", re.IGNORECASE)
_DOI = re.compile(r"(10\.\d{4,9}/[^\s\"<>]+)")


def parse_reference(text):
    ref = (text or "").strip()
    if not ref or len(ref) > 300:
        return None

    m = _ARXIV_URL.search(ref)
    if m:
        return ("arxiv", m.group(1))

    bare = re.sub(r"^arxiv:\s*", "", ref, flags=re.IGNORECASE)
    if _ARXIV_ID.match(bare):
        return ("arxiv", bare)

    m = _DOI.search(ref)
    if m:
        doi = m.group(1).rstrip(".,;)")
        arxiv = _ARXIV_DOI.match(doi)
        if arxiv:
            return ("arxiv", arxiv.group(1))
        return ("doi", doi.lower())
    return None
