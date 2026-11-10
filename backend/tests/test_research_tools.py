"""研究工作流工具，離線 stub。"""
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


# --- BibTeX（純函式） ---

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


# ------

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


def test_bibtex_keys_are_unique_within_one_export():
    papers = [{"id": f"240{i}.0000{i}", "title": "Retrieval at scale", "authors": "Ada Lovelace",
               "published": "2026-01-01"} for i in range(3)]
    bib = to_bibtex(papers)
    keys = [line.split("{", 1)[1].rstrip(",") for line in bib.splitlines()
            if line.startswith("@misc{")]
    assert keys == ["ada2026retrieval", "ada2026retrievala", "ada2026retrievalb"]


def test_bibtex_authors_are_joined_with_and():
    bib = to_bibtex([{"id": "1", "title": "T", "authors": "Ada Lovelace, Alan Turing, Grace Hopper"}])
    assert "author = {Ada Lovelace and Alan Turing and Grace Hopper}" in bib


def test_bibtex_doi_papers_use_doi_not_arxiv_fields():
    bib = to_bibtex([{"id": "doi:10.1000/xyz", "title": "T", "authors": "A", "source": "doi",
                      "link": "https://doi.org/10.1000/xyz"}])
    assert "doi = {10.1000/xyz}" in bib
    assert "archivePrefix" not in bib and "eprint" not in bib


def test_bibtex_non_arxiv_sources_have_no_eprint():
    bib = to_bibtex([{"id": "news-abc", "title": "T", "source": "rss", "link": "https://e.com"}])
    assert "eprint" not in bib and "url = {https://e.com}" in bib


def test_bibtex_escapes_special_characters():
    bib = to_bibtex([{"id": "1", "title": "50% better: Q&A {with} braces_", "authors": "A"}])
    assert r"title = {50\% better: Q\&A with braces\_}" in bib
    assert bib.count("{") == bib.count("}")
