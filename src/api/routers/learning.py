"""學習路徑與技能端點：主題生成路徑（LLM/檢索式）、勾選進度、技能等級。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.deps import get_current_user, get_store
from src.api.services.product import get_product_service
from src.store.base import Store

router = APIRouter(prefix="/api", tags=["learning"])


class PathBody(BaseModel):
    topic: str = Field(min_length=1, max_length=200)
    steps: int = Field(default=6, ge=2, le=12)


class PathUpdateBody(BaseModel):
    topic: str | None = None
    items: list[dict] | None = None
    progress: dict | None = None


class SkillBody(BaseModel):
    skill: str = Field(min_length=1, max_length=80)
    level: int = Field(ge=0, le=100)


@router.get("/learning-paths")
def list_paths(user=Depends(get_current_user), store: Store = Depends(get_store)):
    return {"items": store.list_learning_paths(user["id"])}


@router.post("/learning-paths", status_code=201)
def create_path(body: PathBody, user=Depends(get_current_user)):
    return get_product_service().generate_learning_path(
        user["id"], body.topic, steps=body.steps)


@router.patch("/learning-paths/{path_id}")
def update_path(path_id: int, body: PathUpdateBody, user=Depends(get_current_user),
                store: Store = Depends(get_store)):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    updated = store.update_learning_path(path_id, user["id"], **fields)
    if updated is None:
        raise HTTPException(status_code=404, detail="學習路徑不存在")
    return updated


@router.delete("/learning-paths/{path_id}", status_code=204)
def delete_path(path_id: int, user=Depends(get_current_user),
                store: Store = Depends(get_store)):
    if not store.delete_learning_path(path_id, user["id"]):
        raise HTTPException(status_code=404, detail="學習路徑不存在")


@router.get("/skills")
def list_skills(user=Depends(get_current_user), store: Store = Depends(get_store)):
    return {"items": store.list_skills(user["id"])}


@router.put("/skills")
def set_skill(body: SkillBody, user=Depends(get_current_user),
              store: Store = Depends(get_store)):
    return store.set_skill(user["id"], body.skill, body.level)
