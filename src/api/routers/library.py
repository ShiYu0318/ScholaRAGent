"""文庫端點：論文、每日抓取、個人化、互動、閱讀看板、匯出。"""
import io
import zipfile

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from src.api.deps import get_current_user, get_store
from src.api.services.library import get_library_service
from src.store.base import Store

router = APIRouter(prefix="/api", tags=["library"])


@router.get("/papers")
def list_papers(limit: int = 50, source: str | None = None, query: str | None = None,
                _user=Depends(get_current_user)):
    return get_library_service().papers(limit=min(limit, 200), source=source, query=query)


@router.get("/paper/{paper_id}")
def get_paper(paper_id: str, _user=Depends(get_current_user)):
    paper = get_library_service().paper(paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="論文不存在")
    return paper


class DailyBody(BaseModel):
    count: int | None = Field(default=None, ge=1, le=50)


@router.post("/daily")
def fetch_daily(body: DailyBody | None = None, _user=Depends(get_current_user)):
    return get_library_service().daily(count=body.count if body else None)


@router.get("/daily/personalized")
def personalized_daily(top_n: int = 5, user=Depends(get_current_user)):
    items = get_library_service().personalized(user["id"], top_n=min(top_n, 20))
    return {"items": items}


class InteractionBody(BaseModel):
    action: str = Field(min_length=1, max_length=40)
    paper_id: str | None = None
    value: float = 1.0


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
    paper_id: str
    title: str = ""
    state: str = "to-read"
    tags: list[str] = []
    note: str = ""


class ReadingStateBody(BaseModel):
    state: str


@router.get("/reading")
def reading_items(state: str | None = None, user=Depends(get_current_user),
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
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.patch("/reading/{paper_id}")
def reading_set_state(paper_id: str, body: ReadingStateBody,
                      user=Depends(get_current_user), store: Store = Depends(get_store)):
    try:
        ok = store.reading_set_state(user["id"], paper_id, body.state)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
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
