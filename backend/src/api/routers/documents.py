"""產出文件端點：把綜述、報告、比較表、草稿存成可編輯的 Markdown 文件。

研究工具的輸出原本只顯示一次；存成文件後可以接續編修、歸到專案、
連同引用的論文一起匯出。
"""
import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from src.api.deps import get_current_user, get_store
from src.api.validators import PaperId
from src.store.base import Store
from src.tools.research_tools import to_bibtex

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_DOCUMENTS_PER_USER = 500
MAX_CONTENT = 200_000

DocumentKind = Literal["note", "review", "report", "comparison", "deep_research",
                       "outline", "draft"]


class DocumentBody(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(default="", max_length=MAX_CONTENT)
    kind: DocumentKind = "note"
    project_id: int | None = None
    paper_ids: list[PaperId] = Field(default_factory=list, max_length=100)


class DocumentUpdateBody(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, max_length=MAX_CONTENT)
    kind: DocumentKind | None = None
    project_id: int | None = None
    paper_ids: list[PaperId] | None = Field(default=None, max_length=100)


def safe_filename(title, fallback="document"):
    """把標題轉成可放進 Content-Disposition / zip 的檔名（只留字母數字、中日韓文字與 -_）。"""
    name = re.sub(r"[^\w\-]+", "-", title or "", flags=re.UNICODE).strip("-_")[:80]
    return name or fallback


def document_markdown(doc, papers):
    """文件全文 + 參考文獻清單。"""
    lines = [f"# {doc['title']}", "", doc["content"].rstrip()]
    if papers:
        lines += ["", "## References", ""]
        for i, p in enumerate(papers, 1):
            authors = f"{p['authors']}. " if p.get("authors") else ""
            year = f" ({p['published'][:4]})" if p.get("published") else ""
            link = f" <{p['link']}>" if p.get("link") else ""
            lines.append(f"{i}. {authors}{p['title']}{year}.{link}")
    return "\n".join(lines) + "\n"


def _require(doc_id, user, store):
    doc = store.get_document(doc_id, user["id"])
    if doc is None:
        raise HTTPException(status_code=404, detail="文件不存在")
    return doc


@router.get("")
def list_documents(project_id: int | None = None, user=Depends(get_current_user),
                   store: Store = Depends(get_store)):
    return {"items": store.list_documents(user["id"], project_id=project_id)}


@router.post("", status_code=201)
def create_document(body: DocumentBody, user=Depends(get_current_user),
                    store: Store = Depends(get_store)):
    if len(store.list_documents(user["id"])) >= MAX_DOCUMENTS_PER_USER:
        raise HTTPException(status_code=422, detail=f"最多 {MAX_DOCUMENTS_PER_USER} 份文件")
    try:
        return store.create_document(
            user["id"], body.title.strip(), content=body.content, kind=body.kind,
            project_id=body.project_id, paper_ids=body.paper_ids)
    except ValueError:
        raise HTTPException(status_code=404, detail="專案不存在")


@router.get("/{doc_id}")
def get_document(doc_id: int, user=Depends(get_current_user),
                 store: Store = Depends(get_store)):
    doc = _require(doc_id, user, store)
    doc["papers"] = store.get_papers(doc["paper_ids"])
    return doc


@router.patch("/{doc_id}")
def update_document(doc_id: int, body: DocumentUpdateBody,
                    user=Depends(get_current_user), store: Store = Depends(get_store)):
    _require(doc_id, user, store)
    # 只送出用戶端實際帶的欄位：project_id 明確給 null 代表移出專案
    fields = body.model_dump(exclude_unset=True)
    try:
        return store.update_document(doc_id, user["id"], **fields)
    except ValueError:
        raise HTTPException(status_code=404, detail="專案不存在")


@router.delete("/{doc_id}", status_code=204)
def delete_document(doc_id: int, user=Depends(get_current_user),
                    store: Store = Depends(get_store)):
    if not store.delete_document(doc_id, user["id"]):
        raise HTTPException(status_code=404, detail="文件不存在")


@router.get("/{doc_id}/export")
def export_document(doc_id: int,
                    format: Literal["md", "bib"] = Query(default="md"),
                    user=Depends(get_current_user), store: Store = Depends(get_store)):
    """下載文件：md 為全文加參考文獻，bib 為引用論文的 BibTeX。"""
    doc = _require(doc_id, user, store)
    papers = store.get_papers(doc["paper_ids"])
    name = safe_filename(doc["title"])
    if format == "bib":
        content, media, ext = to_bibtex(papers), "text/plain", "bib"
    else:
        content, media, ext = document_markdown(doc, papers), "text/markdown", "md"
    # 檔名可能含非 ASCII：用 RFC 5987 的 filename* 編碼
    from urllib.parse import quote
    disposition = f"attachment; filename=\"document.{ext}\"; filename*=UTF-8''{quote(name)}.{ext}"
    return Response(content, media_type=f"{media}; charset=utf-8",
                    headers={"Content-Disposition": disposition})
