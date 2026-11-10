"""研究專案端點：專案 CRUD、專案文獻、總覽與匯出。

專案是研究流程的容器：文獻、對話與產出文件都可以歸在某個專案下，
讓「蒐集 → 閱讀 → 提問 → 綜述 → 寫作」在同一個工作區內完成。
"""
import io
import zipfile
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from src.api.deps import get_current_user, get_store
from src.api.validators import PaperId
from src.store.base import Store
from src.tools.research_tools import to_bibtex

router = APIRouter(prefix="/api/projects", tags=["projects"])

MAX_PROJECTS_PER_USER = 100
MAX_PAPERS_PER_PROJECT = 500


class ProjectBody(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    question: str = Field(default="", max_length=1000)


class ProjectUpdateBody(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    question: str | None = Field(default=None, max_length=1000)
    status: Literal["active", "archived"] | None = None


class PaperIdsBody(BaseModel):
    paper_ids: list[PaperId] = Field(min_length=1, max_length=100)


def require_project(project_id, user, store):
    """取得屬於目前使用者的專案；不存在或不屬於他都回 404（不洩漏是否存在）。"""
    project = store.get_project(project_id, user["id"])
    if project is None:
        raise HTTPException(status_code=404, detail="專案不存在")
    return project


@router.get("")
def list_projects(include_archived: bool = False, user=Depends(get_current_user),
                  store: Store = Depends(get_store)):
    return {"items": store.list_projects(user["id"], include_archived=include_archived)}


@router.post("", status_code=201)
def create_project(body: ProjectBody, user=Depends(get_current_user),
                   store: Store = Depends(get_store)):
    if len(store.list_projects(user["id"], include_archived=True)) >= MAX_PROJECTS_PER_USER:
        raise HTTPException(status_code=422, detail=f"最多 {MAX_PROJECTS_PER_USER} 個專案")
    return store.create_project(user["id"], body.name.strip(), question=body.question.strip())


@router.get("/{project_id}")
def get_project(project_id: int, user=Depends(get_current_user),
                store: Store = Depends(get_store)):
    return require_project(project_id, user, store)


@router.patch("/{project_id}")
def update_project(project_id: int, body: ProjectUpdateBody,
                   user=Depends(get_current_user), store: Store = Depends(get_store)):
    require_project(project_id, user, store)
    return store.update_project(project_id, user["id"], **body.model_dump())


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, user=Depends(get_current_user),
                   store: Store = Depends(get_store)):
    if not store.delete_project(project_id, user["id"]):
        raise HTTPException(status_code=404, detail="專案不存在")


# ---- 專案文獻 ----
@router.get("/{project_id}/papers")
def project_papers(project_id: int, user=Depends(get_current_user),
                   store: Store = Depends(get_store)):
    """專案內的論文，並附上該使用者的閱讀狀態、標籤與筆記。"""
    require_project(project_id, user, store)
    reading = {r["id"]: r for r in store.reading_items(user["id"])}
    items = []
    for paper in store.project_papers(project_id, user["id"]):
        r = reading.get(paper["id"])
        paper["reading"] = (
            {"state": r["state"], "tags": r["tags"], "note": r["note"]} if r else None)
        items.append(paper)
    return {"items": items}


@router.post("/{project_id}/papers")
def add_project_papers(project_id: int, body: PaperIdsBody,
                       user=Depends(get_current_user), store: Store = Depends(get_store)):
    project = require_project(project_id, user, store)
    if project["paper_count"] + len(body.paper_ids) > MAX_PAPERS_PER_PROJECT:
        raise HTTPException(status_code=422,
                            detail=f"每個專案最多 {MAX_PAPERS_PER_PROJECT} 篇論文")
    added = store.project_add_papers(project_id, user["id"], body.paper_ids)
    return {"added": added, "project": store.get_project(project_id, user["id"])}


@router.delete("/{project_id}/papers/{paper_id:path}", status_code=204)
def remove_project_paper(project_id: int, paper_id: str,
                         user=Depends(get_current_user), store: Store = Depends(get_store)):
    require_project(project_id, user, store)
    if not store.project_remove_paper(project_id, user["id"], paper_id):
        raise HTTPException(status_code=404, detail="論文不在此專案中")


# ---- 總覽：研究流程進度與下一步 ----
# 研究流程五個階段；每份文件依類型歸到「綜述」或「寫作」
SYNTHESIS_KINDS = ("review", "report", "comparison", "deep_research")
WRITING_KINDS = ("draft", "outline", "note")
STAGES = ("collect", "read", "ask", "synthesize", "write")


def build_overview(project, papers, reading, conversations, documents):
    """由專案內容推導各階段進度與下一步（純函式，方便測試）。"""
    states = [reading[p["id"]]["state"] for p in papers if p["id"] in reading]
    read_counts = {
        "to_read": len(papers) - states.count("reading") - states.count("done"),
        "reading": states.count("reading"),
        "done": states.count("done"),
    }
    synthesis = [d for d in documents if d["kind"] in SYNTHESIS_KINDS]
    writing = [d for d in documents if d["kind"] in WRITING_KINDS]
    stages = {
        "collect": {"count": len(papers), "done": len(papers) > 0},
        "read": {"count": read_counts["done"], "total": len(papers), **read_counts,
                 "done": len(papers) > 0 and read_counts["done"] + read_counts["reading"] > 0},
        "ask": {"count": len(conversations), "done": len(conversations) > 0},
        "synthesize": {"count": len(synthesis), "done": len(synthesis) > 0},
        "write": {"count": len(writing), "done": len(writing) > 0},
    }
    # 下一步 = 第一個還沒開始的階段；全部做過就建議匯出
    next_step = next((s for s in STAGES if not stages[s]["done"]), "export")
    return {
        "project": project,
        "stages": stages,
        "next_step": next_step,
        "recent_documents": documents[:5],
        "recent_conversations": [
            {"id": c["id"], "title": c["title"], "updated_at": c["updated_at"]}
            for c in conversations[:5]],
    }


@router.get("/{project_id}/overview")
def project_overview(project_id: int, user=Depends(get_current_user),
                     store: Store = Depends(get_store)):
    project = require_project(project_id, user, store)
    reading = {r["id"]: r for r in store.reading_items(user["id"])}
    return build_overview(
        project,
        store.project_papers(project_id, user["id"]),
        reading,
        store.list_conversations(user["id"], limit=200, project_id=project_id),
        store.list_documents(user["id"], project_id=project_id),
    )


# ---- 匯出 ----
def _notes_markdown(papers, reading):
    lines = ["# Reading notes", ""]
    for p in papers:
        r = reading.get(p["id"])
        lines.append(f"## {p['title']}")
        meta = [x for x in (p.get("authors"), (p.get("published") or "")[:4], p.get("link")) if x]
        if meta:
            lines.append(" · ".join(meta))
        if r:
            lines.append(f"- Status: {r['state']}")
            if r["tags"]:
                lines.append(f"- Tags: {', '.join(r['tags'])}")
            if r["note"]:
                lines += ["", r["note"].strip()]
        lines.append("")
    return "\n".join(lines)


def _readme_markdown(project, papers, documents):
    lines = [f"# {project['name']}", ""]
    if project.get("question"):
        lines += ["**Research question:** " + project["question"], ""]
    lines += [f"- Papers: {len(papers)} (`references.bib`, `notes.md`)",
              f"- Documents: {len(documents)} (`documents/`)", ""]
    if papers:
        lines += ["## Papers", ""]
        lines += [f"{i}. {p['title']}" + (f" — {p['link']}" if p.get("link") else "")
                  for i, p in enumerate(papers, 1)]
    return "\n".join(lines) + "\n"


@router.get("/{project_id}/export")
def export_project(project_id: int, user=Depends(get_current_user),
                   store: Store = Depends(get_store)):
    """把專案打包成 zip：參考文獻、閱讀筆記與所有文件，可直接帶到 Overleaf / Obsidian。"""
    from src.api.routers.documents import document_markdown, safe_filename

    project = require_project(project_id, user, store)
    papers = store.project_papers(project_id, user["id"])
    reading = {r["id"]: r for r in store.reading_items(user["id"])}
    documents = [store.get_document(d["id"], user["id"])
                 for d in store.list_documents(user["id"], project_id=project_id)]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README.md", _readme_markdown(project, papers, documents))
        zf.writestr("references.bib", to_bibtex(papers))
        zf.writestr("notes.md", _notes_markdown(papers, reading))
        used = set()
        for doc in documents:
            # 檔名只取清理過的標題（不含路徑分隔），重名時加上文件 id
            name = safe_filename(doc["title"])
            if name in used:
                name = f"{name}-{doc['id']}"
            used.add(name)
            zf.writestr(f"documents/{name}.md",
                        document_markdown(doc, store.get_papers(doc["paper_ids"])))
    filename = quote(safe_filename(project["name"], "project"))
    return Response(
        buf.getvalue(), media_type="application/zip",
        headers={"Content-Disposition":
                 f"attachment; filename=\"project.zip\"; filename*=UTF-8''{filename}.zip"})
