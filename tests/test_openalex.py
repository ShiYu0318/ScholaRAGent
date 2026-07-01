"""OpenAlex 引用資料 client（v2/C1），注入式 fetch，離線。"""
from src.crawlers.openalex import OpenAlexClient


class FakeFetch:
    def __init__(self, reply):
        self.reply = reply
        self.urls = []

    def __call__(self, url):
        self.urls.append(url)
        return self.reply


_WORK = {
    "id": "https://openalex.org/W4387561528",
    "title": "Mistral 7B",
    "cited_by_count": 292,
    "referenced_works": ["https://openalex.org/W1", "https://openalex.org/W2"],
}


def test_work_by_arxiv_strips_version_and_uses_doi():
    ff = FakeFetch(_WORK)
    client = OpenAlexClient(fetch=ff)
    w = client.work_by_arxiv("2310.06825v2")
    assert "10.48550/arXiv.2310.06825" in ff.urls[0]     # 版本號被去除
    assert "v2" not in ff.urls[0].split("arXiv.")[-1].split("?")[0]
    assert w["cited_by_count"] == 292
    assert w["references"] == ["W1", "W2"]               # 去掉 URL 前綴
    assert w["openalex_id"] == "W4387561528"


def test_citation_count():
    client = OpenAlexClient(fetch=FakeFetch(_WORK))
    assert client.citation_count("2310.06825") == 292


def test_returns_none_on_fetch_error():
    def boom(url):
        raise RuntimeError("network down")
    client = OpenAlexClient(fetch=boom)
    assert client.work_by_arxiv("2310.06825") is None
    assert client.citation_count("2310.06825") == 0


def test_cited_by_returns_normalized_citing_works():
    reply = {"results": [
        {"id": "https://openalex.org/W10", "title": "Citing A", "cited_by_count": 3,
         "referenced_works": [], "publication_year": 2024},
        {"id": "https://openalex.org/W11", "title": "Citing B", "cited_by_count": 1,
         "referenced_works": [], "publication_year": 2025},
    ]}
    ff = FakeFetch(reply)
    client = OpenAlexClient(fetch=ff)
    out = client.cited_by("W1", limit=5)
    assert "filter=cites:W1" in ff.urls[0]
    assert [w["openalex_id"] for w in out] == ["W10", "W11"]
    assert out[0]["title"] == "Citing A"


class RoutingFetch:
    """DOI 查詢失敗、標題搜尋成功——模擬舊論文（無 arXiv DOI）。"""
    def __init__(self, search_work):
        self.search_work = search_work

    def __call__(self, url):
        if "doi:" in url:
            raise RuntimeError("404")
        return {"results": [self.search_work]}


def test_falls_back_to_title_search_when_doi_missing():
    client = OpenAlexClient(fetch=RoutingFetch(_WORK))
    w = client.work_by_arxiv("1706.03762", title="Attention Is All You Need")
    assert w["cited_by_count"] == 292


def test_no_title_fallback_returns_none():
    def only_doi_fails(url):
        raise RuntimeError("404")
    client = OpenAlexClient(fetch=only_doi_fails)
    assert client.work_by_arxiv("1706.03762") is None      # 無 title 就不搜尋
