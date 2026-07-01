"""GraphRAG 社群偵測與圖檢索（C3 / C4），建立在 [concept_graph] 之上。

- C3 detect_communities/summarize_communities：把概念圖分成研究子領域社群，
  各生成一段摘要，支援「這個領域整體在做什麼」的全局問題。
- C4 neighborhood/graph_context：從種子概念沿邊擴展，取出相關關係作為 LLM
  的圖檢索脈絡，支援路徑式推理（「A 的方法被誰改進？」）。

純 networkx，離線可測；上雲時可換 Neo4j 但介面不變。
"""
import networkx as nx

from src.utils.logger import get_logger

_logger = get_logger("graph_rag")

_SYSTEM = (
    "以下是一個研究概念社群中的關係三元組。請用一句話總結這個子領域在研究什麼。"
    "只輸出這句話。"
)


def detect_communities(graph):
    """回傳社群清單（每個為節點集合）。空圖回空清單。"""
    if graph.number_of_nodes() == 0:
        return []
    undirected = graph.to_undirected()
    comms = nx.community.greedy_modularity_communities(undirected)
    return [set(c) for c in comms]


def summarize_communities(graph, llm):
    """對每個社群生成 {nodes, summary}。"""
    out = []
    for nodes in detect_communities(graph):
        sub = graph.subgraph(nodes)
        rels = "\n".join(
            f"{u} | {d.get('relation', '')} | {v}" for u, v, d in sub.edges(data=True)
        )
        try:
            summary = llm._chat(_SYSTEM, rels, max_tokens=120)
        except Exception as e:
            _logger.error(f"社群摘要失敗：{e}")
            summary = ""
        out.append({"nodes": sorted(nodes), "summary": summary})
    return out


def neighborhood(graph, seed, hops=1):
    """回傳種子概念 hops 跳內的節點集合（無向擴展）；不存在回空集合。"""
    if seed not in graph:
        return set()
    ego = nx.ego_graph(graph.to_undirected(as_view=True), seed, radius=hops)
    return set(ego.nodes())


def graph_context(graph, seeds, hops=1):
    """把種子鄰域的關係整理成文字，供 LLM 圖檢索作答時 grounding。"""
    nodes = set()
    for s in seeds:
        nodes |= neighborhood(graph, s, hops=hops)
    lines = []
    for u, v, d in graph.subgraph(nodes).edges(data=True):
        lines.append(f"{u} --{d.get('relation', '')}--> {v}")
    return "\n".join(lines)
