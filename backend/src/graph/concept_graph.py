"""概念知識圖抽取。

讓 LLM 從論文摘要抽出 (head | relation | tail) 三元組（如 方法/資料集/任務/指標
之間的關係），彙整成 networkx 有向圖。邊上記錄出處論文 id，供之後圖檢索、
社群摘要與路徑推理使用。離線可用 stub LLM 測試抽取與建圖。
"""
import networkx as nx

from src.utils.logger import get_logger

_logger = get_logger("concept_graph")

_SYSTEM = (
    "從這篇論文抽取知識三元組，描述方法／資料集／任務／指標之間的關係。"
    "每行一個，格式嚴格為 `head | relation | tail`。只輸出三元組，不要多餘說明。"
)


def extract_triples(paper, llm):
    """回傳 [(head, relation, tail)]；解析失敗或 LLM 出錯回空清單。"""
    user = f"標題：{paper.get('title', '')}\n摘要：{paper.get('abstract', '')}"
    try:
        out = llm._chat(_SYSTEM, user, max_tokens=300) or ""
    except Exception as e:
        _logger.error(f"三元組抽取失敗：{e}")
        return []

    triples = []
    for line in out.splitlines():
        parts = [x.strip() for x in line.split("|")]
        if len(parts) == 3 and all(parts):
            triples.append((parts[0], parts[1], parts[2]))
    return triples


def build_concept_graph(papers, llm):
    """從多篇論文建立概念有向圖；重複的邊合併並累積出處論文 id。"""
    g = nx.DiGraph()
    for p in papers:
        pid = p.get("id")
        for head, rel, tail in extract_triples(p, llm):
            if g.has_edge(head, tail):
                g[head][tail]["papers"].add(pid)
            else:
                g.add_edge(head, tail, relation=rel, papers={pid})
    _logger.info(f"概念圖：{g.number_of_nodes()} 節點 / {g.number_of_edges()} 邊")
    return g
