"""檢索式 ReAct agent（Agentic RAG / B1）。

不再「一次檢索、一次作答」，而是多輪：先檢索→看已找到什麼→由 LLM 決定
是否需要換角度再查（丟出下一個查詢或 DONE）。適合需要多跳、多面向的複雜問題。

`retrieve` 為 `retrieve(query, k) -> [(paper, score)]` 的可呼叫物件（如混合檢索）。
可獨立於 LangGraph 運作；未來要用狀態機重構時，此類別即單一節點的邏輯。
"""
from src.utils.logger import get_logger

_SYSTEM = (
    "你是研究檢索代理。根據原始問題與目前已找到的論文標題，判斷是否需要用"
    "不同角度再檢索一次。若需要，只輸出一個新的英文檢索查詢；若資訊已足夠，"
    "只輸出 DONE。不要多餘說明。"
)


class ResearchAgent:
    def __init__(self, llm, retrieve):
        self.logger = get_logger(self.__class__.__name__)
        self.llm = llm
        self.retrieve = retrieve

    def gather(self, question, max_rounds=3, k=4):
        """多輪檢索並累積去重的論文清單（依發現順序）。"""
        found, seen = [], set()
        query = question
        for round_i in range(max_rounds):
            for paper, _ in self.retrieve(query, k=k):
                if paper["id"] not in seen:
                    seen.add(paper["id"])
                    found.append(paper)
            if round_i == max_rounds - 1:
                break
            nxt = self._next_query(question, found)
            if not nxt or nxt.strip().upper() == "DONE":
                break
            query = nxt.strip()
        return found

    def _next_query(self, question, found):
        titles = "\n".join(f"- {p.get('title', '')}" for p in found)
        user = f"原始問題：{question}\n已找到：\n{titles}"
        try:
            return self.llm._chat(_SYSTEM, user, max_tokens=60)
        except Exception as e:
            self.logger.error(f"決定下一查詢失敗，結束檢索：{e}")
            return "DONE"
