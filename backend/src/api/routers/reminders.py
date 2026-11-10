"""情境化提醒端點：CRUD + 標記完成；到期推播由 scheduler 輪詢。"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.validators import BoundedJson, IsoDatetime
from src.api.deps import get_current_user, get_store
from src.store.base import Store

router = APIRouter(prefix="/api", tags=["reminders"])

MAX_ACTIVE_REMINDERS = 200


class ReminderBody(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    due_at: IsoDatetime = Field(description="ISO 時間，如 2026-07-03T09:00:00")
    context: Annotated[dict | None, BoundedJson(2000)] = None


@router.get("/reminders")
def list_reminders(include_done: bool = False, user=Depends(get_current_user),
                   store: Store = Depends(get_store)):
    return {"items": store.list_reminders(user["id"], include_done=include_done)}


@router.post("/reminders", status_code=201)
def add_reminder(body: ReminderBody, user=Depends(get_current_user),
                 store: Store = Depends(get_store)):
    if len(store.list_reminders(user["id"])) >= MAX_ACTIVE_REMINDERS:
        raise HTTPException(status_code=422,
                            detail=f"未完成的提醒最多 {MAX_ACTIVE_REMINDERS} 則")
    return store.add_reminder(user["id"], body.text, body.due_at, context=body.context)


@router.post("/reminders/{reminder_id}/complete")
def complete_reminder(reminder_id: int, user=Depends(get_current_user),
                      store: Store = Depends(get_store)):
    if not store.complete_reminder(reminder_id, user["id"]):
        raise HTTPException(status_code=404, detail="提醒不存在")
    return {"ok": True}


@router.delete("/reminders/{reminder_id}", status_code=204)
def delete_reminder(reminder_id: int, user=Depends(get_current_user),
                    store: Store = Depends(get_store)):
    if not store.delete_reminder(reminder_id, user["id"]):
        raise HTTPException(status_code=404, detail="提醒不存在")
