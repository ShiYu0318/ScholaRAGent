"""引用圖 PageRank 影響力（v2/C7）。"""
import networkx as nx

from src.graph.graph_rag import influential_papers


def test_ranks_most_cited_node_first():
    g = nx.DiGraph()
    for citing in ("A", "B", "C"):
        g.add_edge(citing, "S")      # 三篇都引用 S → S 入度最高
    out = influential_papers(g, top_n=1)
    assert out[0][0] == "S"


def test_top_n_limits_results():
    g = nx.DiGraph()
    g.add_edge("A", "S")
    g.add_edge("B", "T")
    assert len(influential_papers(g, top_n=2)) == 2


def test_scores_descending():
    g = nx.DiGraph()
    g.add_edge("A", "S"); g.add_edge("B", "S"); g.add_edge("C", "T")
    out = influential_papers(g, top_n=5)
    scores = [s for _, s in out]
    assert scores == sorted(scores, reverse=True)


def test_empty_graph_returns_empty():
    assert influential_papers(nx.DiGraph()) == []
