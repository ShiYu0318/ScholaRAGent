"""Modular RAG 可組合管線。

把 RAG 各步驟抽象成「stage：state -> state」，用 RAGPipeline 自由組裝／重排／
增減，實現 Modular RAG 的核心精神——同一套模組能組成不同流程（例如
查詢轉換->混合檢索->精排->生成，或省略某步、換不同檢索器）。

state 是一個 dict，慣例鍵：query / papers / answer。stage factories 把既有元件
包成 stage，彼此解耦、好測。
"""
from src.utils.logger import get_logger

_logger = get_logger("RAGPipeline")


class RAGPipeline:
    def __init__(self, stages=None):
        self.stages = list(stages or [])

    def add(self, stage):
        """附加一個 stage，回傳自身以便串接。"""
        self.stages.append(stage)
        return self

    def run(self, query, **initial):
        """依序執行各 stage，回傳最終 state。"""
        state = {"query": query, **initial}
        for stage in self.stages:
            state = stage(state)
        return state


def retrieve_stage(retrieve_fn):
    """retrieve_fn(query) -> [paper]，寫入 state['papers']。"""
    def stage(state):
        state["papers"] = retrieve_fn(state["query"])
        return state
    return stage


def rerank_stage(rerank_fn):
    """rerank_fn(query, papers) -> [paper]，更新 state['papers']。"""
    def stage(state):
        state["papers"] = rerank_fn(state["query"], state.get("papers", []))
        return state
    return stage


def generate_stage(generate_fn):
    """generate_fn(query, papers) -> str，寫入 state['answer']。"""
    def stage(state):
        state["answer"] = generate_fn(state["query"], state.get("papers", []))
        return state
    return stage
