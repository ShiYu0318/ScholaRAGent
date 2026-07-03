"""RSS 訂閱源與主題訂閱端點（每人自訂）。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, HttpUrl

from src.api.deps import get_current_user, get_store
from src.api.services.library import get_library_service
from src.store.base import Store

router = APIRouter(prefix="/api", tags=["feeds"])


class FeedBody(BaseModel):
    url: HttpUrl
    title: str | None = None
    category: str | None = None


class FeedUpdateBody(BaseModel):
    title: str | None = None
    category: str | None = None
    enabled: bool | None = None


@router.get("/feeds")
def list_feeds(user=Depends(get_current_user), store: Store = Depends(get_store)):
    return {"items": store.list_feeds(user["id"])}


@router.post("/feeds", status_code=201)
def add_feed(body: FeedBody, user=Depends(get_current_user),
             store: Store = Depends(get_store)):
    try:
        return store.add_feed(user["id"], str(body.url), title=body.title,
                              category=body.category)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.patch("/feeds/{feed_id}")
def update_feed(feed_id: int, body: FeedUpdateBody, user=Depends(get_current_user),
                store: Store = Depends(get_store)):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    updated = store.update_feed(feed_id, user["id"], **fields)
    if updated is None:
        raise HTTPException(status_code=404, detail="feed 不存在")
    return updated


@router.delete("/feeds/{feed_id}", status_code=204)
def delete_feed(feed_id: int, user=Depends(get_current_user),
                store: Store = Depends(get_store)):
    if not store.delete_feed(feed_id, user["id"]):
        raise HTTPException(status_code=404, detail="feed 不存在")


@router.post("/feeds/refresh")
def refresh_feeds(user=Depends(get_current_user)):
    return get_library_service().refresh_feeds(user["id"])


# ---- 主題訂閱（關鍵字）----
class SubscriptionBody(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    keywords: list[str] = Field(min_length=1)


@router.get("/subscriptions")
def list_subscriptions(user=Depends(get_current_user),
                       store: Store = Depends(get_store)):
    return {"items": store.list_subscriptions(user["id"])}


@router.post("/subscriptions", status_code=201)
def add_subscription(body: SubscriptionBody, user=Depends(get_current_user),
                     store: Store = Depends(get_store)):
    return store.add_subscription(user["id"], body.name, body.keywords)


@router.delete("/subscriptions/{name}", status_code=204)
def remove_subscription(name: str, user=Depends(get_current_user),
                        store: Store = Depends(get_store)):
    if not store.remove_subscription(user["id"], name):
        raise HTTPException(status_code=404, detail="訂閱不存在")
