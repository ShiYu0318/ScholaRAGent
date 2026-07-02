"""圖譜服務：引用網路 / 概念圖 / 全域搜尋，輸出 D3 可直接吃的 nodes/edges。

networkx 圖 -> {nodes, edges}；附 PageRank（節點大小）與社群編號（著色）。
OpenAlex client 與 LLM 皆可注入替身，離線測試不打外部服務。
概念圖建置需逐篇呼叫 LLM，故快取於記憶體，refresh=true 才重建。
"""
import re
import threading

import networkx as nx

from src.crawlers.openalex import OpenAlexClient
from src.graph.citation_network import build_citation_graph
from src.graph.concept_graph import build_concept_graph
from src.graph.global_search import global_search
from src.graph.graph_rag import detect_communities, summarize_communities
from src.llm.groq_client import GroqClient
from src.utils.logger import get_logger


def to_d3(graph):
    """networkx 圖 -> D3 資料；附 pagerank 與（無向）社群編號。"""
    if graph.number_of_nodes() == 0:
        return {"nodes": [], "edges": []}
    pr = nx.pagerank(graph) if graph.number_of_edges() else {}
    community_of = {}
    for i, nodes in enumerate(detect_communities(graph)):
        for n in nodes:
            community_of[n] = i

    nodes = []
    for n, data in graph.nodes(data=True):
        nodes.append({
            "id": str(n),
            "label": data.get("title") or str(n),
            "kind": data.get("kind", "concept"),
            "year": data.get("year"),
            "cited_by_count": data.get("cited_by_count"),
            "pagerank": round(pr.get(n, 0.0), 6),
            "community": community_of.get(n, 0),
        })
    edges = [
        {
            "source": str(u),
            "target": str(v),
            "relation": d.get("relation", ""),
            "papers": sorted(d["papers"]) if isinstance(d.get("papers"), set) else d.get("papers"),
        }
        for u, v, d in graph.edges(data=True)
    ]
    return {"nodes": nodes, "edges": edges}


class GraphService:
    def __init__(self, store, llm=None, openalex=None):
        self.logger = get_logger(self.__class__.__name__)
        self.store = store
        self._llm = llm
        self._openalex = openalex
        self._lock = threading.Lock()
        self._citation_cache = {}      # seed -> nx graph
        self._concept_graph = None
        self._communities = None       # [{nodes, summary}]

    @property
    def llm(self):
        if self._llm is None:
            self._llm = GroqClient()
        return self._llm

    @property
    def openalex(self):
        if self._openalex is None:
            self._openalex = OpenAlexClient()
        return self._openalex

    _ARXIV_ID = re.compile(r"^(arXiv:)?\d{4}\.\d{4,5}(v\d+)?$")

    def citation(self, seed, title=None):
        """種子論文的引用網路（快取）；回傳 D3 資料 + 影響力排行。

        種子不像 arXiv 編號時視為論文標題（OpenAlex 標題搜尋），
        讓「貼編號」與「打標題」都能展開。
        """
        key = (seed or "").strip()
        if title is None and key and not self._ARXIV_ID.match(key):
            title = key
        with self._lock:
            graph = self._citation_cache.get(key)
        if graph is None:
            graph = build_citation_graph(key, self.openalex, title=title)
            if graph.number_of_nodes() > 0:  # 空圖多半是查無或網路失敗，不快取
                with self._lock:
                    self._citation_cache[key] = graph
        data = to_d3(graph)
        top = sorted(data["nodes"], key=lambda n: n["pagerank"], reverse=True)[:10]
        data["influential"] = [
            {"id": n["id"], "label": n["label"], "pagerank": n["pagerank"]} for n in top
        ]
        return data

    def concept(self, limit=30, refresh=False, summarize=False):
        """概念圖（LLM 三元組抽取，快取）；可選社群摘要。"""
        with self._lock:
            cached = self._concept_graph
        if cached is None or refresh:
            papers = self.store.all_papers(limit=limit)
            cached = build_concept_graph(papers, self.llm)
            with self._lock:
                self._concept_graph = cached
                self._communities = None
        data = to_d3(cached)
        if summarize:
            data["communities"] = self._get_communities(cached)
        return data

    def _get_communities(self, graph):
        with self._lock:
            if self._communities is not None:
                return self._communities
        comms = summarize_communities(graph, self.llm)
        with self._lock:
            self._communities = comms
        return comms

    def global_answer(self, query, limit=30):
        """全域搜尋：社群摘要 map-reduce 回答宏觀問題。"""
        data_graph = None
        with self._lock:
            data_graph = self._concept_graph
        if data_graph is None:
            papers = self.store.all_papers(limit=limit)
            data_graph = build_concept_graph(papers, self.llm)
            with self._lock:
                self._concept_graph = data_graph
        communities = self._get_communities(data_graph)
        answer = global_search(query, communities, self.llm)
        return {"answer": answer, "communities": communities}


_service = None
_service_lock = threading.Lock()


def get_graph_service():
    global _service
    with _service_lock:
        if _service is None:
            from src.store import get_store
            _service = GraphService(get_store())
    return _service


def set_graph_service(service):
    """測試注入；回傳先前實例。"""
    global _service
    prev, _service = _service, service
    return prev
