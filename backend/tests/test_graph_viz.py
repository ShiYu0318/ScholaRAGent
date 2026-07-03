"""概念圖視覺化匯出。"""
import networkx as nx

from src.graph.visualize import to_mermaid


def _g():
    g = nx.DiGraph()
    g.add_edge("Transformer", "attention", relation="uses")
    g.add_edge("BERT", "Transformer", relation="based_on")
    return g


def test_mermaid_has_header_and_edges():
    out = to_mermaid(_g())
    assert out.splitlines()[0] == "graph LR"
    assert "Transformer" in out and "attention" in out
    assert "uses" in out              # 關係標在邊上


def test_mermaid_sanitizes_node_ids():
    g = nx.DiGraph()
    g.add_edge("graph neural nets", "GNN", relation="abbrev")
    out = to_mermaid(g)
    # 節點 id 不含空白（避免 Mermaid 解析錯誤），但標籤保留原文
    assert "graph neural nets" in out          # 標籤原文
    assert "graph neural nets[" not in out     # id 不能直接用原文


def test_mermaid_empty_graph():
    assert to_mermaid(nx.DiGraph()) == "graph LR"
