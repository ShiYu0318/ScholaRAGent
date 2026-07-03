"""洞察端點：趨勢偵測、週報、使用者閱讀分析。"""
from fastapi import APIRouter, Depends, Query

from src.api.deps import get_current_user
from src.api.services.product import get_product_service

router = APIRouter(prefix="/api", tags=["insights"])


@router.get("/trends")
def trends(granularity: str = Query(default="month", pattern="^(month|year)$"),
           top: int = Query(default=10, ge=1, le=30),
           user=Depends(get_current_user)):
    return get_product_service().trends(granularity=granularity, top_n=top)


@router.get("/trends/{keyword}")
def keyword_trend(keyword: str,
                  granularity: str = Query(default="month", pattern="^(month|year)$"),
                  user=Depends(get_current_user)):
    return get_product_service().keyword_series(keyword, granularity=granularity)


@router.get("/digest/weekly")
def weekly_digest(user=Depends(get_current_user)):
    return get_product_service().weekly_digest(user["id"])


@router.get("/analytics")
def analytics(days: int = Query(default=14, ge=1, le=90),
              user=Depends(get_current_user)):
    return get_product_service().analytics(user["id"], days=days)
