"""健康監控端點：儲存後端統計 + 服務狀態（階段 7 擴充排程/外部服務）。"""
from fastapi import APIRouter, Depends

from src.api.deps import get_store
from src.store.base import Store

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health(store: Store = Depends(get_store)):
    return {"status": "ok", "store": store.stats()}
