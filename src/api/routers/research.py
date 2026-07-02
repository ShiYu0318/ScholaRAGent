"""研究端點：深度研究（SSE）、文獻綜述、比較、報告、BibTeX、白話解讀。"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.api.deps import get_current_user
from src.api.routers.ask import sse
from src.api.services.research import get_research_service

router = APIRouter(prefix="/api", tags=["research"])


class TopicBody(BaseModel):
    topic: str = Field(min_length=1, max_length=500)
    k: int = Field(default=8, ge=1, le=20)


class CompareBody(BaseModel):
    topic: str | None = None
    paper_ids: list[str] | None = None
    k: int = Field(default=6, ge=2, le=20)


class DeepResearchBody(BaseModel):
    topic: str = Field(min_length=1, max_length=500)
    max_subs: int = Field(default=4, ge=1, le=8)
    k: int = Field(default=4, ge=1, le=10)


@router.post("/deepresearch")
def deepresearch(body: DeepResearchBody, _user=Depends(get_current_user)):
    service = get_research_service()

    def gen():
        try:
            for event in service.stream_deepresearch(body.topic, max_subs=body.max_subs,
                                                     k=body.k):
                yield sse(event)
        except Exception as e:
            yield sse({"type": "error", "message": f"深度研究失敗：{e}"})

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


@router.post("/litreview")
def litreview(body: TopicBody, _user=Depends(get_current_user)):
    return get_research_service().litreview(body.topic, k=body.k)


@router.post("/compare")
def compare(body: CompareBody, _user=Depends(get_current_user)):
    if not body.topic and not body.paper_ids:
        raise HTTPException(status_code=422, detail="需提供 topic 或 paper_ids")
    return get_research_service().compare(topic=body.topic, paper_ids=body.paper_ids,
                                          k=body.k)


@router.post("/report")
def report(body: TopicBody, _user=Depends(get_current_user)):
    return get_research_service().report(body.topic, k=body.k)


@router.post("/bibtex")
def bibtex(body: CompareBody, _user=Depends(get_current_user)):
    if not body.topic and not body.paper_ids:
        raise HTTPException(status_code=422, detail="需提供 topic 或 paper_ids")
    return get_research_service().bibtex(topic=body.topic, paper_ids=body.paper_ids)


@router.post("/explain")
def explain(body: dict, _user=Depends(get_current_user)):
    paper_id = (body or {}).get("paper_id", "")
    if not paper_id:
        raise HTTPException(status_code=422, detail="需提供 paper_id")
    result = get_research_service().explain(paper_id)
    if result is None:
        raise HTTPException(status_code=404, detail="論文不存在")
    return result
