"""補充端點：資料來源狀態、個人記憶、RAG 評估指標、工具代理。

memory 與 agent 走模組級注入點（測試替身）；agent 需 GROQ_API_KEY，
未設定時回 503（與 OAuth provider 降級同一慣例）。
"""
import threading

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src import config
from src.api.deps import get_current_user, get_store
from src.rag.evaluation import faithfulness, precision_at_k, recall, reciprocal_rank
from src.store.base import Store

router = APIRouter(prefix="/api", tags=["extras"])


# ---- 資料來源 ----
@router.get("/sources")
def sources(user=Depends(get_current_user), store: Store = Depends(get_store)):
    feeds = store.list_feeds(user["id"])
    return {"items": [
        {"name": "arxiv", "configured": True, "detail": config.ARXIV_QUERY},
        {"name": "hackernews", "configured": True, "detail": None},
        {"name": "github", "configured": True,
         "detail": "token" if config.GITHUB_TOKEN else "anonymous"},
        {"name": "reddit", "configured": True, "detail": None},
        {"name": "rss", "configured": bool(feeds), "detail": f"{len(feeds)} feeds"},
        {"name": "x", "configured": bool(config.X_BEARER_TOKEN), "detail": None},
    ]}


# ---- 個人記憶 ----
_memory = None
_memory_lock = threading.Lock()


def get_memory():
    global _memory
    with _memory_lock:
        if _memory is None:
            from src.memory.memory_store import MemoryStore
            _memory = MemoryStore()
    return _memory


def set_memory(memory):
    """測試注入；回傳先前實例。"""
    global _memory
    prev, _memory = _memory, memory
    return prev


class MemoryBody(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    kind: str = Field(default="note", max_length=40)


@router.get("/memory")
def list_memory(kind: str | None = None, contains: str | None = None,
                limit: int = 50, user=Depends(get_current_user)):
    items = get_memory().filter(str(user["id"]), kind=kind,
                                contains=contains, limit=limit)
    return {"items": items}


@router.post("/memory", status_code=201)
def add_memory(body: MemoryBody, user=Depends(get_current_user)):
    return get_memory().add(str(user["id"]), body.content, kind=body.kind)


# ---- RAG 評估 ----
_judge_llm = None
_judge_lock = threading.Lock()


def get_judge_llm():
    global _judge_llm
    with _judge_lock:
        if _judge_llm is None:
            if not config.GROQ_API_KEY:
                raise HTTPException(status_code=503,
                                    detail="未設定 GROQ_API_KEY，judge 評估不可用")
            from src.llm.groq_client import GroqClient
            _judge_llm = GroqClient()
    return _judge_llm


def set_judge_llm(llm):
    """測試注入；回傳先前實例。"""
    global _judge_llm
    prev, _judge_llm = _judge_llm, llm
    return prev


class EvalBody(BaseModel):
    engine: str = Field(default="offline", pattern="^(offline|judge)$")
    # offline：確定性排序/重疊指標
    retrieved_ids: list[str] | None = None
    relevant_ids: list[str] | None = None
    k: int = Field(default=4, ge=1, le=50)
    # judge：RAGAS 式 LLM-as-judge 指標
    question: str | None = None
    answer: str | None = None
    contexts: list[str] | None = None
    ground_truth: str | None = None


@router.post("/eval")
def evaluate(body: EvalBody, user=Depends(get_current_user)):
    if body.engine == "judge":
        if not (body.question and body.answer and body.contexts):
            raise HTTPException(status_code=422,
                                detail="judge 模式需要 question、answer、contexts")
        from src.rag.llm_judge import evaluate_answer
        return evaluate_answer(get_judge_llm(), body.question, body.answer,
                               body.contexts, ground_truth=body.ground_truth)

    if not (body.retrieved_ids and body.relevant_ids):
        raise HTTPException(status_code=422,
                            detail="offline 模式需要 retrieved_ids、relevant_ids")
    result = {
        "precision_at_k": precision_at_k(body.retrieved_ids, body.relevant_ids, body.k),
        "recall": recall(body.retrieved_ids, body.relevant_ids),
        "mrr": reciprocal_rank(body.retrieved_ids, body.relevant_ids),
    }
    if body.answer and body.contexts:
        result["faithfulness"] = faithfulness(body.answer, body.contexts)
    return result


# ---- 工具代理 ----
_agent = None
_agent_lock = threading.Lock()


def get_tool_agent():
    global _agent
    with _agent_lock:
        if _agent is None:
            if not config.GROQ_API_KEY:
                raise HTTPException(status_code=503, detail="未設定 GROQ_API_KEY，代理不可用")
            from src.agent.tool_agent import ToolAgent
            from src.llm.groq_client import GroqClient
            from src.store import get_store as _get_store
            from src.tools.builtins import build_default_registry
            llm = GroqClient()
            registry = build_default_registry(store=_get_store().vector)
            _agent = ToolAgent(llm.client, registry, llm.model)
    return _agent


def set_tool_agent(agent):
    """測試注入；回傳先前實例。"""
    global _agent
    prev, _agent = _agent, agent
    return prev


class AgentBody(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    max_steps: int = Field(default=5, ge=1, le=10)


@router.post("/agent")
def run_agent(body: AgentBody, user=Depends(get_current_user)):
    answer = get_tool_agent().run(body.message, max_steps=body.max_steps)
    return {"answer": answer}
