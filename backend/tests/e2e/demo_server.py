"""Self-contained backend for UI tests and local demos.

Runs the real API and serves the built frontend, but with a throwaway data
directory, a hash-based fake embedder, a canned LLM and stubbed paper sources —
so it needs no credentials, downloads no models and never calls out.

    cd frontend && npm run build
    cd ../backend && uv run python -m tests.e2e.demo_server --port 8765
"""
import argparse
import hashlib
import os
import tempfile
from pathlib import Path

ANSWER = (
    "Based on the papers in scope, RAG systems are evaluated along three axes:\n\n"
    "1. **Retrieval quality** — precision@k and recall of the retrieved passages [1].\n"
    "2. **Faithfulness** — whether each claim is supported by the retrieved context [2].\n"
    "3. **Citation accuracy** — whether a cited source really backs the sentence.\n"
)
REVIEW = (
    "## Themes\n\n**Automated evaluation**: RAGAS [1] and ARES [2] both use LLM judges.\n\n"
    "| Method | Needs labels | Metrics |\n|---|---|---|\n"
    "| RAGAS | No | faithfulness |\n| ARES | Few | context relevance |\n\n"
    "## Gaps\n\n- No shared benchmark for multi-hop questions.\n"
)
PAPERS = [
    ("2309.15217", "RAGAS: Automated Evaluation of Retrieval Augmented Generation",
     "Shahul Es, Jithin James", "2023-09-26",
     "A framework for reference-free evaluation of RAG pipelines. Code: https://github.com/explodinggradients/ragas"),
    ("2311.09476", "ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems",
     "Jon Saad-Falcon, Omar Khattab", "2023-11-16",
     "ARES evaluates RAG systems along context relevance, answer faithfulness and answer relevance."),
    ("2005.11401", "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
     "Patrick Lewis, Ethan Perez", "2020-05-22",
     "Models which combine parametric and non-parametric memory for language generation."),
    ("2312.10997", "Retrieval-Augmented Generation for Large Language Models: A Survey",
     "Yunfan Gao, Yun Xiong", "2023-12-18",
     "This survey reviews Naive RAG, Advanced RAG and Modular RAG."),
]


def _paper(row):
    pid, title, authors, published, abstract = row
    return {"id": pid, "title": title, "authors": authors, "published": published,
            "abstract": abstract, "link": f"https://arxiv.org/abs/{pid}", "source": "arxiv"}


class FakeEmbedder:
    dim = 64

    def encode(self, texts):
        import numpy as np
        out = []
        for text in texts:
            vec = np.zeros(self.dim, dtype="float32")
            for tok in str(text).lower().split():
                vec[int(hashlib.md5(tok.encode()).hexdigest(), 16) % self.dim] += 1
            norm = np.linalg.norm(vec)
            out.append(vec / norm if norm else vec)
        return np.asarray(out, dtype="float32")


class FakeLLM:
    model, client = "demo", None

    def _chat(self, system, user, **kwargs):
        return REVIEW

    def stream_answer(self, question, papers, history=None):
        for i in range(0, len(ANSWER), 16):
            yield ANSWER[i:i + 16]

    def answer(self, question, papers):
        return "Retrieval and generation need to be evaluated separately [1]."

    def research_report(self, topic, papers):
        return REVIEW

    def compare_papers(self, papers):
        return REVIEW

    def latex_draft(self, topic, papers=None):
        return "\\section{Introduction}"

    def review_suggestions(self, text):
        return "- The second paragraph needs a citation."

    def slides_outline(self, topic, papers=None):
        return "1. Motivation\n2. Method\n3. Results"

    def summarize(self, paper):
        return "Summary."


class StubArxiv:
    """All four papers are searchable; none is in the library until imported."""

    def search_topic(self, topic, limit=8):
        return [_paper(r) for r in PAPERS[:limit]]

    def fetch_by_ids(self, ids):
        known = {r[0]: r for r in PAPERS}
        return [_paper(known[i]) for i in ids if i in known]

    def fetch_latest_papers(self, limit=5):
        return []


class StubOpenAlex:
    def work_by_arxiv(self, arxiv_id, title=None):
        return {"cited_by_count": 412}

    def paper_by_doi(self, doi):
        return None


def build_app(data_dir):
    """Create the FastAPI app wired to stubs. Must run before anything imports src.config."""
    os.environ.update({
        "GROQ_API_KEY": "demo-not-real", "GROQ_BASE_URL": "http://127.0.0.1:9/v1",
        "JWT_SECRET": "", "APP_ENV": "development", "SCHEDULER_ENABLED": "0",
        "STORE_BACKEND": "sqlite", "DATABASE_URL": "", "RATE_LIMIT_ENABLED": "0",
    })
    from src import config
    data_dir = Path(data_dir)
    config.DATA_DIR = data_dir
    for name in ("INDEX_PATH", "METADATA_PATH", "DB_PATH", "MEMORY_PATH", "TASKS_PATH",
                 "SCHEDULE_PATH"):
        setattr(config, name, data_dir / Path(getattr(config, name)).name)

    from src import store as store_module
    from src.api.services import ask, library, research
    from src.store.sqlite_faiss import SqliteFaissStore

    embedder, llm = FakeEmbedder(), FakeLLM()
    store = SqliteFaissStore(db_path=data_dir / "demo.db", embedder=embedder)
    store_module.set_store(store)
    ask_service = ask.AskService(store, llm=llm)
    ask.set_ask_service(ask_service)
    research.set_research_service(research.ResearchService(store, llm=llm, ask_service=ask_service))
    library.set_library_service(library.LibraryService(
        store, arxiv=StubArxiv(), openalex=StubOpenAlex(), embedder=embedder))

    from src.api.app import create_app
    return create_app()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", default=None)
    args = parser.parse_args()
    data_dir = args.data_dir or tempfile.mkdtemp(prefix="scholaragent-demo-")
    import uvicorn
    uvicorn.run(build_app(data_dir), host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
