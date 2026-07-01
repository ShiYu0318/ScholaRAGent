"""研究工作流工具（v2/D2,D3,D4,D6），離線 stub。"""
from src.tools.research_tools import (
    to_bibtex, literature_review, comparison_table, explain_paper,
)


def _paper(**kw):
    base = {"id": "2501.12345", "title": "Attention Is All You Need",
            "authors": "Vaswani, A. et al.", "published": "2017-06-12",
            "link": "http://arxiv.org/abs/2501.12345"}
    base.update(kw)
    return base


class StubLLM:
    def __init__(self, reply="OUT"):
        self.reply = reply
        self.seen = []

    def _chat(self, system, user, **kwargs):
        self.seen.append((system, user))
        return self.reply


# --- D3 BibTeX（純函式） ---

def test_to_bibtex_contains_core_fields():
    bib = to_bibtex([_paper()])
    assert "Attention Is All You Need" in bib
    assert "2017" in bib
    assert "2501.12345" in bib          # arXiv eprint id
    assert bib.strip().startswith("@")


def test_bibtex_citation_key_from_author_year_title():
    bib = to_bibtex([_paper()])
    assert "vaswani2017attention" in bib.lower()


def test_to_bibtex_handles_missing_fields():
    bib = to_bibtex([{"id": "x", "title": "Untitled Work"}])
    assert "Untitled Work" in bib          # 缺欄位不崩潰


def test_to_bibtex_empty():
    assert to_bibtex([]) == ""


# --- D2 / D4 / D6（LLM orchestration） ---

def test_literature_review_calls_llm_with_papers():
    llm = StubLLM("REVIEW")
    out = literature_review("graphs", [_paper(title="Paper GNN")], llm)
    assert out == "REVIEW"
    assert "Paper GNN" in llm.seen[0][1]      # 論文有進到 prompt


def test_comparison_table_returns_llm_output():
    assert comparison_table("t", [_paper()], StubLLM("| m | d |")) == "| m | d |"


def test_explain_paper_includes_title_in_prompt():
    llm = StubLLM("EXPLAINED")
    out = explain_paper(_paper(title="Deep Nets"), llm)
    assert out == "EXPLAINED"
    assert "Deep Nets" in llm.seen[0][1]
