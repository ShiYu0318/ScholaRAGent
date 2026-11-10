"""研究專案端點：專案 CRUD、專案文獻、總覽與匯出。

專案是研究流程的容器：文獻、對話與產出文件都可以歸在某個專案下，
讓「蒐集 → 閱讀 → 提問 → 綜述 → 寫作」在同一個工作區內完成。
"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.api.deps import get_current_user, get_store
from src.api.validators import PaperId
from src.store.base import Store

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
