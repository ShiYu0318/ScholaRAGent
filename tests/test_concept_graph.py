"""概念知識圖抽取，離線 stub LLM + networkx。"""
from src.graph.concept_graph import extract_triples, build_concept_graph


def _paper(pid="1", title="T", abstract="A"):
    return {"id": pid, "title": title, "abstract": abstract}


class StubLLM:
    def __init__(self, reply):
        self.reply = reply

    def _chat(self, system, user, **kwargs):
        return self.reply


class BoomLLM:
    def _chat(self, *a, **k):
        raise RuntimeError("down")


def test_extract_triples_parses_pipe_lines():
    llm = StubLLM("Transformer | uses | attention\nBERT | trained_on | Wikipedia")
    triples = extract_triples(_paper(), llm)
    assert ("Transformer", "uses", "attention") in triples
    assert ("BERT", "trained_on", "Wikipedia") in triples


def test_extract_triples_skips_malformed_lines():
    llm = StubLLM("just a sentence\nA | rel | B\nincomplete | pair")
    assert extract_triples(_paper(), llm) == [("A", "rel", "B")]


def test_extract_triples_error_returns_empty():
    assert extract_triples(_paper(), BoomLLM()) == []


def test_build_graph_adds_edges():
    g = build_concept_graph([_paper("1")], StubLLM("A | r | B"))
    assert g.has_edge("A", "B")
    assert g.number_of_nodes() >= 2


def test_build_graph_records_paper_provenance():
    g = build_concept_graph([_paper("1")], StubLLM("A | r | B"))
    assert "1" in g["A"]["B"]["papers"]


def test_build_graph_merges_same_edge_across_papers():
    class TwoReply:
        def __init__(self):
            self.n = 0
        def _chat(self, *a, **k):
            self.n += 1
            return "A | r | B"
    g = build_concept_graph([_paper("1"), _paper("2")], TwoReply())
    assert g["A"]["B"]["papers"] == {"1", "2"}
