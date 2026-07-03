"""研究/寫作服務：深度研究（串流）、文獻工具、寫作工具的薄封裝。

深度研究把 DeepResearcher.run 的流程改成逐步 yield 事件（分解、逐子題
檢索+摘要、綜合、引用），前端能即時看到進度。檢索重用 AskService 的
混合檢索堆疊；LLM 可注入替身離線測試。
"""
import threading

from src.llm.groq_client import GroqClient
from src.rag.citations import format_citations
from src.tools.research_tools import (
    comparison_table,
    explain_paper,
    literature_review,
    to_bibtex,
)
from src.tools.writing_tools import extract_contributions, polish_text, review_checklist
from src.utils.logger import get_logger

_SYNTH_SYSTEM = (
    "你是資深研究者。根據以下各子題的摘要，寫一段統整的綜合結論："
    "指出共識、分歧與研究缺口。條理清楚、繁體中文。"
)


class ResearchService:
    def __init__(self, store, llm=None, ask_service=None):
        self.logger = get_logger(self.__class__.__name__)
        self.store = store
        self._llm = llm
        self._ask = ask_service

    @property
    def llm(self):
        if self._llm is None:
            self._llm = GroqClient()
        return self._llm

    @property
    def ask(self):
        if self._ask is None:
            from src.api.services.ask import get_ask_service
            self._ask = get_ask_service()
        return self._ask

    def _search(self, topic, k=8):
        if self.store.count_papers() == 0:
            return []
        return self.ask._simple_search(topic, k=k)

    # ---- 深度研究（串流事件）----
    def stream_deepresearch(self, topic, max_subs=4, k=4):
        """yield 事件 dict：decompose / section / synthesis / citations / done。"""
        subs = self.ask.transformer.decompose(topic, max_sub=max_subs)
        yield {"type": "decompose", "questions": subs}

        sections, papers, seen = [], [], set()
        for sub in subs:
            sub_papers = self._search(sub, k=k)
            for p in sub_papers:
                if p["id"] not in seen:
                    seen.add(p["id"])
                    papers.append(p)
            summary = self.llm.answer(sub, sub_papers)
            sections.append(f"## {sub}\n{summary}")
            yield {"type": "section", "question": sub, "content": summary,
                   "papers": [p["id"] for p in sub_papers]}

        try:
            synthesis = self.llm._chat(_SYNTH_SYSTEM, "\n\n".join(sections), max_tokens=500)
        except Exception as e:
            self.logger.error(f"綜合失敗：{e}")
            synthesis = "（綜合生成失敗）"
        yield {"type": "synthesis", "content": synthesis}

        from src.api.services.ask import AskService
        yield {"type": "citations", "citations": AskService.citations(papers)}
        yield {"type": "done"}

    # ---- 文獻工具 ----
    def litreview(self, topic, k=8):
        papers = self._search(topic, k=k)
        return {"content": literature_review(topic, papers, self.llm),
                "papers": [p["id"] for p in papers]}

    def compare(self, topic=None, paper_ids=None, k=6):
        if paper_ids:
            papers = [p for pid in paper_ids if (p := self.store.get_paper(pid))]
        else:
            papers = self._search(topic or "", k=k)
        return {"content": comparison_table(topic or "多文件比較", papers, self.llm),
                "papers": [p["id"] for p in papers]}

    def report(self, topic, k=8):
        papers = self._search(topic, k=k)
        return {"content": self.llm.research_report(topic, papers),
                "papers": [p["id"] for p in papers]}

    def bibtex(self, topic=None, paper_ids=None, k=8):
        if paper_ids:
            papers = [p for pid in paper_ids if (p := self.store.get_paper(pid))]
        else:
            papers = self._search(topic or "", k=k)
        return {"content": to_bibtex(papers), "papers": [p["id"] for p in papers]}

    def explain(self, paper_id):
        paper = self.store.get_paper(paper_id)
        if paper is None:
            return None
        return {"content": explain_paper(paper, self.llm), "papers": [paper_id]}

    # ---- 寫作工具 ----
    def write(self, tool, text="", topic=""):
        """tool: polish | contributions | checklist | latex | slides | review。"""
        if tool == "polish":
            return polish_text(text, self.llm)
        if tool == "contributions":
            return extract_contributions(text, self.llm)
        if tool == "checklist":
            return review_checklist(topic or text, self.llm)
        if tool == "latex":
            papers = self._search(topic, k=5) if topic else []
            return self.llm.latex_draft(topic or text, papers)
        if tool == "slides":
            papers = self._search(topic, k=5) if topic else []
            return self.llm.slides_outline(topic or text, papers)
        if tool == "review":
            return self.llm.review_suggestions(text)
        raise ValueError(f"未知寫作工具：{tool}")


_service = None
_service_lock = threading.Lock()


def get_research_service():
    global _service
    with _service_lock:
        if _service is None:
            from src.store import get_store
            _service = ResearchService(get_store())
    return _service


def set_research_service(service):
    """測試注入；回傳先前實例。"""
    global _service
    prev, _service = _service, service
    return prev
