"""對話端點：列表/搜尋、讀取、改名、刪除、分享。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src import config
from src.api.deps import get_current_user, get_store
from src.store.base import Store

router = APIRouter(prefix="/api", tags=["conversations"])


class RenameBody(BaseModel):
    title: str = Field(min_length=1, max_length=200)


@router.get("/conversations")
def list_conversations(query: str | None = None, limit: int = 50,
                       user=Depends(get_current_user),
                       store: Store = Depends(get_store)):
    items = store.list_conversations(user["id"], query=query, limit=min(limit, 200))
    return {"items": items}


@router.get("/conversations/{conv_id}")
def get_conversation(conv_id: int, user=Depends(get_current_user),
                     store: Store = Depends(get_store)):
    conv = store.get_conversation(conv_id, user_id=user["id"])
    if conv is None:
        raise HTTPException(status_code=404, detail="對話不存在")
    return conv


@router.patch("/conversations/{conv_id}")
def rename_conversation(conv_id: int, body: RenameBody,
                        user=Depends(get_current_user),
                        store: Store = Depends(get_store)):
    if not store.rename_conversation(conv_id, user["id"], body.title):
        raise HTTPException(status_code=404, detail="對話不存在")
    return store.get_conversation(conv_id, user_id=user["id"])


@router.delete("/conversations/{conv_id}", status_code=204)
def delete_conversation(conv_id: int, user=Depends(get_current_user),
                        store: Store = Depends(get_store)):
    if not store.delete_conversation(conv_id, user["id"]):
        raise HTTPException(status_code=404, detail="對話不存在")


@router.post("/conversations/{conv_id}/share")
def share_conversation(conv_id: int, user=Depends(get_current_user),
                       store: Store = Depends(get_store)):
    token = store.share_conversation(conv_id, user["id"])
    if token is None:
        raise HTTPException(status_code=404, detail="對話不存在")
    return {"token": token, "url": f"{config.FRONTEND_URL}/#/shared/{token}"}


@router.get("/shared/{token}")
def shared_conversation(token: str, store: Store = Depends(get_store)):
    """公開分享頁：不需登入，只露出標題與訊息。"""
    conv = store.get_shared_conversation(token)
    if conv is None:
        raise HTTPException(status_code=404, detail="分享連結無效")
    return {
        "title": conv["title"],
        "created_at": conv["created_at"],
        "messages": [
            {"role": m["role"], "content": m["content"], "citations": m["citations"]}
            for m in conv["messages"]
        ],
    }
