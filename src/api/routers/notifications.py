"""通知偏好端點：頻率/時區/勿擾/頻道，儲存後即時重排該使用者的排程任務。"""
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.api.deps import get_current_user, get_store
from src.store.base import Store

router = APIRouter(prefix="/api", tags=["notifications"])

Channel = Literal["web", "telegram", "email", "line"]


class PreferencesBody(BaseModel):
    frequency: Literal["daily", "weekly", "off"] | None = None
    hour: int | None = Field(default=None, ge=0, le=23)
    minute: int | None = Field(default=None, ge=0, le=59)
    timezone: str | None = None
    quiet_start: int | None = Field(default=None, ge=0, le=23)
    quiet_end: int | None = Field(default=None, ge=0, le=23)
    min_score: float | None = Field(default=None, ge=0.0)
    dedupe: bool | None = None
    channels: list[Channel] | None = None


@router.get("/notifications/preferences")
def get_preferences(user=Depends(get_current_user), store: Store = Depends(get_store)):
    return store.get_notification_prefs(user["id"])


@router.put("/notifications/preferences")
def put_preferences(body: PreferencesBody, user=Depends(get_current_user),
                    store: Store = Depends(get_store)):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    prefs = store.set_notification_prefs(user["id"], **fields)
    from src.scheduler import get_scheduler_manager
    get_scheduler_manager().schedule_user(user["id"])
    return prefs
