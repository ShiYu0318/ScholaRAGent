"""引用網路建構（v2/C6，paper_master 啟發），離線 stub client。"""
from src.graph.citation_network import build_citation_graph


class StubClient:
    def work_by_arxiv(self, arxiv_id, title=None):
        return {"openalex_id": "S", "title": "Seed Paper",
                "references": ["R1", "R2"], "year": 2023, "cited_by_count": 10}

    def cited_by(self, openalex_id, limit=25):
        return [{"openalex_id": "D1", "title": "Derivative One",
                 "year": 2024, "cited_by_count": 1}]


class NotFoundClient:
    def work_by_arxiv(self, arxiv_id, title=None):
        return None


def test_graph_has_seed_prior_and_derivative():
    g = build_citation_graph("2310.06825", StubClient())
    assert g.nodes["S"]["kind"] == "seed"
    assert g.nodes["R1"]["kind"] == "prior"
    assert g.nodes["D1"]["kind"] == "derivative"


def test_edge_directions_follow_citation():
    g = build_citation_graph("x", StubClient())
    assert g.has_edge("S", "R1")     # 種子引用先前研究（prior）
    assert g.has_edge("D1", "S")     # 後續研究引用種子（derivative）


def test_respects_max_refs_and_cites():
    g = build_citation_graph("x", StubClient(), max_refs=1, max_cites=1)
    priors = [n for n, d in g.nodes(data=True) if d.get("kind") == "prior"]
    assert priors == ["R1"]


def test_empty_graph_when_seed_not_found():
    assert build_citation_graph("x", NotFoundClient()).number_of_nodes() == 0
