"""Eval testset builder（Advanced RAG / E8，受 meetGRAG 啟發）。

從收錄的論文自動生成「黃金問答題組」：對每篇論文請 LLM 出可由該篇回答的問題，
以該篇為正解文件（relevant）。產出可直接餵 [eval_harness].evaluate_retrieval
做回歸，量化每次 RAG 改動的成效。離線 stub 可測。
"""
import re

from src.utils.logger import get_logger

_logger = get_logger("testset_builder")
_NUM = re.compile(r"^\s*(?:\d+[.)、]|[-*•])\s*")

_SYSTEM = (
    "根據這篇論文，出 {n} 個「能由本篇內容回答」的檢索問題，每行一個、"
    "不要編號、不要多餘說明。"
)


def _questions(paper, llm, n):
    system = _SYSTEM.format(n=n)
    user = f"標題：{paper.get('title', '')}\n摘要：{paper.get('abstract', '')}"
    out = llm._chat(system, user, max_tokens=200) or ""
    qs = [_NUM.sub("", line).strip() for line in out.splitlines()]
    return [q for q in qs if q][:n]


def build_testset(papers, llm, per_paper=1):
    """回傳 [{query, relevant:[paper_id], source_paper}]。某篇失敗則略過。"""
    testset = []
    for p in papers:
        try:
            for q in _questions(p, llm, per_paper):
                testset.append({"query": q, "relevant": [p["id"]], "source_paper": p["id"]})
        except Exception as e:
            _logger.error(f"為論文 {p.get('id')} 生成題目失敗：{e}")
    return testset


def validate_testset(testset):
    """濾掉空問題或無正解文件的題目。"""
    return [
        {"query": t["query"], "relevant": t["relevant"]}
        for t in testset
        if t.get("query", "").strip() and t.get("relevant")
    ]
