"""Modular RAG 可組合管線。"""
from src.rag.pipeline import (
    RAGPipeline, retrieve_stage, rerank_stage, generate_stage,
)


def test_runs_stages_in_order():
    log = []

    def s1(st):
        log.append("s1"); st["a"] = 1; return st

    def s2(st):
        log.append("s2"); st["b"] = st["a"] + 1; return st

    out = RAGPipeline([s1, s2]).run("q")
    assert log == ["s1", "s2"]
    assert out["query"] == "q" and out["b"] == 2


def test_empty_pipeline_returns_initial_state():
    assert RAGPipeline([]).run("q") == {"query": "q"}


def test_initial_kwargs_passthrough():
    assert RAGPipeline([]).run("q", k=5)["k"] == 5


def test_add_stage_is_chainable():
    p = RAGPipeline().add(lambda st: {**st, "x": 1}).add(lambda st: {**st, "y": 2})
    out = p.run("q")
    assert out["x"] == 1 and out["y"] == 2


def test_retrieve_stage_sets_papers():
    st = retrieve_stage(lambda q: [{"id": "1"}])({"query": "q"})
    assert st["papers"] == [{"id": "1"}]


def test_rerank_stage_updates_papers():
    st = rerank_stage(lambda q, papers: list(reversed(papers)))({"query": "q", "papers": [1, 2, 3]})
    assert st["papers"] == [3, 2, 1]


def test_generate_stage_sets_answer():
    st = generate_stage(lambda q, papers: f"ans:{len(papers)}")({"query": "q", "papers": [1, 2]})
    assert st["answer"] == "ans:2"


def test_full_modular_pipeline():
    p = RAGPipeline([
        retrieve_stage(lambda q: [{"id": "1"}, {"id": "2"}]),
        rerank_stage(lambda q, papers: papers[:1]),
        generate_stage(lambda q, papers: f"got {len(papers)}"),
    ])
    out = p.run("q")
    assert out["answer"] == "got 1"
    assert [p["id"] for p in out["papers"]] == ["1"]
