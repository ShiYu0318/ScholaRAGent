"""引用網路建構（GraphRAG / C6，受 paper_master 啟發）。

從一篇種子論文展開它的**引用脈絡**：
- prior works（先前研究）：種子的參考文獻，edge = 種子 --cites--> 先前研究。
- derivative works（後續研究）：引用種子的論文，edge = 後續研究 --cites--> 種子。

回傳 networkx DiGraph，可直接餵給 [graph_rag] 的鄰域檢索、[graph.visualize]
的 Mermaid 匯出、C7 PageRank。用 [OpenAlex] client（需 work_by_arxiv/cited_by），
離線用 stub 測、真 API 可驗證。
"""
import networkx as nx

from src.utils.logger import get_logger

_logger = get_logger("citation_network")


def build_citation_graph(seed_arxiv_id, client, title=None, max_refs=20, max_cites=25):
    """建立種子論文的引用網路（prior + derivative）。查不到種子回空圖。"""
    g = nx.DiGraph()
    seed = client.work_by_arxiv(seed_arxiv_id, title=title)
    if not seed:
        return g

    sid = seed["openalex_id"]
    g.add_node(sid, title=seed.get("title", ""), kind="seed",
               year=seed.get("year"), cited_by_count=seed.get("cited_by_count", 0))

    for ref in seed.get("references", [])[:max_refs]:
        if not g.has_node(ref):
            g.add_node(ref, kind="prior")
        g.add_edge(sid, ref, relation="cites")

    for w in client.cited_by(sid, limit=max_cites):
        wid = w["openalex_id"]
        g.add_node(wid, title=w.get("title", ""), kind="derivative",
                   year=w.get("year"), cited_by_count=w.get("cited_by_count", 0))
        g.add_edge(wid, sid, relation="cites")

    _logger.info(f"引用網路：{g.number_of_nodes()} 節點 / {g.number_of_edges()} 邊")
    return g
