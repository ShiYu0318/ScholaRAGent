"""多 agent 協作管線（Agentic RAG / B5）。

Planner → Retriever → Writer → Critic 分工：Critic 把關事實與涵蓋度，不合格
就帶著意見回到 Writer 修訂（上限 max_revisions）。角色以可呼叫物件注入，
編排邏輯本身即可離線測試；實務上各角色接 LLM / 檢索器。
"""
from src.utils.logger import get_logger


class MultiAgentPipeline:
    def __init__(self, planner, retrieve, writer, critic, max_revisions=1):
        self.logger = get_logger(self.__class__.__name__)
        self.planner = planner       # planner(question) -> [subquestion]
        self.retrieve = retrieve     # retrieve(subquestion) -> [paper]
        self.writer = writer         # writer(question, contexts, issues=None) -> draft
        self.critic = critic         # critic(question, draft, contexts) -> (ok, issues)
        self.max_revisions = max_revisions

    def run(self, question):
        subs = self.planner(question)
        contexts = []
        for sub in subs:
            contexts.extend(self.retrieve(sub))

        draft = self.writer(question, contexts)
        for i in range(self.max_revisions):
            ok, issues = self.critic(question, draft, contexts)
            if ok:
                break
            self.logger.info(f"Critic 打回第 {i + 1} 版，依意見修訂")
            draft = self.writer(question, contexts, issues=issues)
        return draft
