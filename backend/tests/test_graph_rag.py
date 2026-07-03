"""GraphRAG 社群偵測 + 圖檢索，離線 networkx + stub。"""
import networkx as nx

from src.graph.graph_rag import (
    detect_communities, summarize_communities, neighborhood, graph_context,
)


def _two_clusters():
    g = nx.DiGraph()
    for u, v in [("a", "b"), ("b", "c"), ("c", "a")]:
        g.add_edge(u, v, relation="r", papers={"1"})
    for u, v in [("x", "y"), ("y", "z"), ("z", "x")]:
        g.add_edge(u, v, relation="r", papers={"2"})
    return g


class StubLLM:
    def _chat(self, system, user, **kwargs):
        return "SUMMARY"


# ------

def test_detect_communities_groups_connected_nodes():
    comms = detect_communities(_two_clusters())
    idx = {n: i for i, c in enumerate(comms) for n in c}
    assert idx["a"] == idx["b"] == idx["c"]
    assert idx["x"] == idx["y"] == idx["z"]
    assert idx["a"] != idx["x"]


def test_summarize_communities_returns_summary_per_group():
    out = summarize_communities(_two_clusters(), StubLLM())
    assert len(out) == 2
    assert all(item["summary"] == "SUMMARY" for item in out)
    assert all(item["nodes"] for item in out)


# ------

def test_neighborhood_within_hops():
    g = nx.DiGraph()
    g.add_edge("a", "b"); g.add_edge("b", "c"); g.add_edge("c", "d")
    assert neighborhood(g, "a", hops=1) == {"a", "b"}
    assert neighborhood(g, "a", hops=2) == {"a", "b", "c"}


def test_graph_context_lists_relations():
    g = nx.DiGraph()
    g.add_edge("Transformer", "attention", relation="uses", papers={"1"})
    ctx = graph_context(g, ["Transformer"], hops=1)
    assert "Transformer" in ctx and "attention" in ctx and "uses" in ctx


def test_neighborhood_missing_node_empty():
    assert neighborhood(nx.DiGraph(), "ghost", hops=1) == set()
