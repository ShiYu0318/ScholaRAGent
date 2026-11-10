"""研究端點：深度研究（SSE）、文獻綜述、比較、報告、BibTeX、白話解讀。"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.api.ratelimit import heavy_limit, llm_limit
from src.api.validators import PaperId
from src.api.deps import get_current_user, get_store
from src.api.routers.ask import sse
from src.api.services.research import get_research_service
from src.store.base import Store
from src.utils.logger import get_logger

router = APIRouter(prefix="/api", tags=["research"])
logger = get_logger("api.research")


class SourceScope(BaseModel):
    """文獻來源：指定專案或論文清單時，只用那些文獻；否則搜尋整個文庫。"""
    project_id: int | None = None
    paper_ids: list[PaperId] | None = Field(default=None, max_length=50)


def resolve_scope(body, user, store):
    """回傳限定的 paper id 清單，或 None（不限定）。專案不屬於使用者回 404。"""
    scope = body.paper_ids
    if body.project_id is not None:
        project_papers = store.project_paper_ids(body.project_id, user["id"])
        if project_papers is None:
            raise HTTPException(status_code=404, detail="專案不存在")
        if scope is None:
            scope = project_papers
    return scope


class TopicBody(SourceScope):
    topic: str = Field(min_length=1, max_length=500)
    k: int = Field(default=8, ge=1, le=20)


class CompareBody(SourceScope):
    topic: str | None = Field(default=None, max_length=500)
    k: int = Field(default=6, ge=2, le=20)


class ExplainBody(BaseModel):
    paper_id: PaperId


class DeepResearchBody(SourceScope):
    topic: str = Field(min_length=1, max_length=500)
    max_subs: int = Field(default=4, ge=1, le=8)
    k: int = Field(default=4, ge=1, le=10)


@router.post("/deepresearch", dependencies=[Depends(heavy_limit)])
def deepresearch(body: DeepResearchBody, user=Depends(get_current_user),
                 store: Store = Depends(get_store)):
    service = get_research_service()
    scope = resolve_scope(body, user, store)

    def gen():
        try:
            for event in service.stream_deepresearch(body.topic, max_subs=body.max_subs,
                                                     k=body.k, paper_ids=scope):
                yield sse(event)
        except Exception:
            logger.exception("深度研究失敗")
            yield sse({"type": "error", "message": "深度研究失敗，請稍後再試"})

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


@router.post("/litreview", dependencies=[Depends(llm_limit)])
def litreview(body: TopicBody, user=Depends(get_current_user),
              store: Store = Depends(get_store)):
    return get_research_service().litreview(body.topic, k=body.k,
                                            paper_ids=resolve_scope(body, user, store))


@router.post("/compare", dependencies=[Depends(llm_limit)])
def compare(body: CompareBody, user=Depends(get_current_user),
            store: Store = Depends(get_store)):
    scope = resolve_scope(body, user, store)
    if not body.topic and not scope:
        raise HTTPException(status_code=422, detail="需提供 topic、paper_ids 或有文獻的專案")
    return get_research_service().compare(topic=body.topic, paper_ids=scope, k=body.k)


@router.post("/report", dependencies=[Depends(llm_limit)])
def report(body: TopicBody, user=Depends(get_current_user),
           store: Store = Depends(get_store)):
    return get_research_service().report(body.topic, k=body.k,
                                         paper_ids=resolve_scope(body, user, store))


@router.post("/bibtex")
def bibtex(body: CompareBody, user=Depends(get_current_user),
           store: Store = Depends(get_store)):
    scope = resolve_scope(body, user, store)
    if not body.topic and not scope:
        raise HTTPException(status_code=422, detail="需提供 topic、paper_ids 或有文獻的專案")
    return get_research_service().bibtex(topic=body.topic, paper_ids=scope)


@router.post("/explain", dependencies=[Depends(llm_limit)])
def explain(body: ExplainBody, _user=Depends(get_current_user)):
    result = get_research_service().explain(body.paper_id)
    if result is None:
        raise HTTPException(status_code=404, detail="論文不存在")
    return result
