"""文庫端點：論文、每日抓取、個人化、互動、閱讀看板、匯出。"""
import io
import zipfile

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from src.api.ratelimit import heavy_limit, llm_limit
from src.api.validators import PaperId, Tag
from src.api.deps import get_current_user, get_store
from src.api.services.library import get_library_service
from src.store.base import Store

router = APIRouter(prefix="/api", tags=["library"])

ReadingState = Literal["to-read", "reading", "done"]


@router.get("/papers")
def list_papers(limit: int = Query(default=50, ge=1, le=200),
                source: str | None = Query(default=None, max_length=40),
                query: str | None = Query(default=None, max_length=200),
                _user=Depends(get_current_user)):
    return get_library_service().papers(limit=limit, source=source, query=query)


@router.get("/paper/{paper_id}")
def get_paper(paper_id: str, _user=Depends(get_current_user)):
    paper = get_library_service().paper(paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="論文不存在")
    return paper


class DailyBody(BaseModel):
    count: int | None = Field(default=None, ge=1, le=50)


@router.post("/daily", dependencies=[Depends(heavy_limit)])
def fetch_daily(body: DailyBody | None = None, _user=Depends(get_current_user)):
    return get_library_service().daily(count=body.count if body else None)


@router.get("/daily/personalized")
def personalized_daily(top_n: int = Query(default=5, ge=1, le=20), user=Depends(get_current_user)):
    items = get_library_service().personalized(user["id"], top_n=top_n)
    return {"items": items}


class InteractionBody(BaseModel):
    # action 會成為偏好模型的特徵名；value 會加總進全站排序，必須有界
    action: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")
    paper_id: PaperId | None = None
    value: float = Field(default=1.0, ge=-5.0, le=5.0)


@router.post("/interactions", status_code=201)
def log_interaction(body: InteractionBody, user=Depends(get_current_user),
                    store: Store = Depends(get_store)):
    try:
        store.log_interaction(body.action, paper_id=body.paper_id,
                              user_id=user["id"], value=body.value)
    except Exception:
        raise HTTPException(status_code=422, detail="互動記錄失敗（論文不存在？）")
    return {"ok": True}


# ---- 閱讀看板 ----
class ReadingBody(BaseModel):
    paper_id: PaperId
    title: str = Field(default="", max_length=500)
    state: ReadingState = "to-read"
    tags: list[Tag] = Field(default_factory=list, max_length=20)
    note: str = Field(default="", max_length=5000)


class ReadingStateBody(BaseModel):
    state: ReadingState


@router.get("/reading")
def reading_items(state: ReadingState | None = None, user=Depends(get_current_user),
                  store: Store = Depends(get_store)):
    return {"items": store.reading_items(user["id"], state=state)}


@router.post("/reading", status_code=201)
def reading_add(body: ReadingBody, user=Depends(get_current_user),
                store: Store = Depends(get_store)):
    title = body.title
    if not title:
        paper = store.get_paper(body.paper_id)
        title = paper["title"] if paper else body.paper_id
    try:
        return store.reading_upsert(user["id"], body.paper_id, title,
                                    state=body.state, tags=body.tags, note=body.note)
    except ValueError:
        raise HTTPException(status_code=422, detail="無效的閱讀狀態")


@router.patch("/reading/{paper_id}")
def reading_set_state(paper_id: str, body: ReadingStateBody,
                      user=Depends(get_current_user), store: Store = Depends(get_store)):
    try:
        ok = store.reading_set_state(user["id"], paper_id, body.state)
    except ValueError:
        raise HTTPException(status_code=422, detail="無效的閱讀狀態")
    if not ok:
        raise HTTPException(status_code=404, detail="閱讀項目不存在")
    return {"ok": True}


@router.delete("/reading/{paper_id}", status_code=204)
def reading_remove(paper_id: str, user=Depends(get_current_user),
                   store: Store = Depends(get_store)):
    if not store.reading_remove(user["id"], paper_id):
        raise HTTPException(status_code=404, detail="閱讀項目不存在")


# ---- 匯出 ----
@router.get("/export/csv")
def export_csv(_user=Depends(get_current_user)):
    content = get_library_service().export_csv()
    return Response(content, media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=papers.csv"})


@router.get("/export/bibtex")
def export_bibtex(_user=Depends(get_current_user)):
    content = get_library_service().export_bibtex()
    return Response(content, media_type="text/plain",
                    headers={"Content-Disposition": "attachment; filename=papers.bib"})


@router.get("/export/obsidian")
def export_obsidian(_user=Depends(get_current_user)):
    notes = get_library_service().export_obsidian()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in notes.items():
            zf.writestr(name, content)
    return Response(buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": "attachment; filename=obsidian-vault.zip"})
