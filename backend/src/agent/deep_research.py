"""深度研究模式——對標 Deep Research。

把一個大主題拆成子問題，逐一檢索並摘要，最後合成一篇含引用的綜述。
每個元件都可注入，離線 stub 即可測整條流程。
"""
from src.rag.citations import format_citations
from src.utils.logger import get_logger

_SYNTH_SYSTEM = (
    "你是資深研究者。根據以下各子題的摘要，寫一段統整的綜合結論："
    "指出共識、分歧與研究缺口。條理清楚、繁體中文。"
)


class DeepResearcher:
    def __init__(self, llm, retrieve, transformer):
        self.logger = get_logger(self.__class__.__name__)
        self.llm = llm
        self.retrieve = retrieve
        self.transformer = transformer

    def run(self, topic, max_subs=4, k=4):
        """回傳 (report_markdown, papers)。"""
        subs = self.transformer.decompose(topic, max_sub=max_subs)
        sections, papers, seen = [], [], set()

        for sub in subs:
            hits = self.retrieve(sub, k=k)
            sub_papers = [p for p, _ in hits]
            for p in sub_papers:
                if p["id"] not in seen:
                    seen.add(p["id"])
                    papers.append(p)
            summary = self.llm.answer(sub, sub_papers)
            sections.append(f"## {sub}\n{summary}")

        synthesis = self._synthesize(sections)
        body = (f"# 深度研究：{topic}\n\n"
                + "\n\n".join(sections)
                + f"\n\n## 綜合\n{synthesis}")
        cites = format_citations(papers)
        report = f"{body}\n\n{cites}" if cites else body
        return report, papers

    def _synthesize(self, sections):
        try:
            joined = "\n\n".join(sections)
            return self.llm._chat(_SYNTH_SYSTEM, joined, max_tokens=500)
        except Exception as e:
            self.logger.error(f"綜合失敗：{e}")
            return "（綜合生成失敗）"
