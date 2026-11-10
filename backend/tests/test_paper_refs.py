"""論文識別碼解析：arXiv ID / 連結 / DOI。"""
import pytest

from src.crawlers.openalex import OpenAlexClient, _abstract_from_index
from src.tools.paper_refs import parse_reference


@pytest.mark.parametrize("text,expected", [
    ("2401.12345", ("arxiv", "2401.12345")),
    ("2401.12345v3", ("arxiv", "2401.12345v3")),
    ("arXiv:1706.03762", ("arxiv", "1706.03762")),
    ("  ARXIV: 1706.03762 ", ("arxiv", "1706.03762")),
    ("https://arxiv.org/abs/1706.03762v7", ("arxiv", "1706.03762v7")),
    ("https://arxiv.org/pdf/1706.03762.pdf", ("arxiv", "1706.03762")),
    ("cs/0301001", ("arxiv", "cs/0301001")),
    ("hep-th/9901001", ("arxiv", "hep-th/9901001")),
    ("https://arxiv.org/abs/math.GT/0309136", ("arxiv", "math.GT/0309136")),
    ("10.48550/arXiv.2401.12345", ("arxiv", "2401.12345")),
    ("10.1145/3292500.3330701", ("doi", "10.1145/3292500.3330701")),
    ("https://doi.org/10.1038/S41586-021-03819-2", ("doi", "10.1038/s41586-021-03819-2")),
    ("doi:10.1000/xyz123.", ("doi", "10.1000/xyz123")),
])
def test_parse_reference(text, expected):
    assert parse_reference(text) == expected


@pytest.mark.parametrize("text", ["", None, "attention is all you need", "12345",
                                  "http://evil.example.com/abs/1", "x" * 301])
def test_parse_reference_rejects_non_identifiers(text):
    assert parse_reference(text) is None


def test_abstract_is_rebuilt_from_inverted_index():
    assert _abstract_from_index({"world": [1], "hello": [0], "again": [2]}) == "hello world again"
    assert _abstract_from_index(None) == ""


def test_paper_by_doi_normalises_to_library_shape():
    seen = []

    def fetch(url):
        seen.append(url)
        return {"id": "https://openalex.org/W1", "title": " Deep Things ",
                "abstract_inverted_index": {"We": [0], "study": [1]},
                "authorships": [{"author": {"display_name": "Ada L."}}],
                "publication_date": "2021-05-01",
                "primary_location": {"landing_page_url": "https://example.org/paper"}}

    paper = OpenAlexClient(fetch=fetch).paper_by_doi("10.1000/XYZ")
    assert paper == {"id": "doi:10.1000/xyz", "title": "Deep Things", "abstract": "We study",
                     "authors": "Ada L.", "link": "https://example.org/paper",
                     "published": "2021-05-01", "source": "doi"}
    assert "works/doi:10.1000/XYZ" in seen[0]


def test_paper_by_doi_returns_none_on_failure():
    def boom(url):
        raise RuntimeError("404")
    assert OpenAlexClient(fetch=boom).paper_by_doi("10.1/x") is None
