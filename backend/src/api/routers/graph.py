"""圖譜端點：引用網路、概念圖、全域搜尋。"""
from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.ratelimit import heavy_limit, llm_limit
from src.api.deps import get_current_user
from src.api.services.graph import get_graph_service

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/citation", dependencies=[Depends(llm_limit)])
def citation_graph(seed: str = Query(min_length=1, max_length=300),
                   title: str | None = Query(default=None, max_length=500),
                   _user=Depends(get_current_user)):
    data = get_graph_service().citation(seed, title=title)
    if not data["nodes"]:
        raise HTTPException(status_code=404, detail="查無此種子論文的引用網路")
    return data


@router.get("/concept", dependencies=[Depends(heavy_limit)])
def concept_graph(limit: int = Query(default=30, ge=1, le=200),
                  refresh: bool = False, summarize: bool = False,
                  _user=Depends(get_current_user)):
    return get_graph_service().concept(limit=limit, refresh=refresh, summarize=summarize)


@router.get("/global", dependencies=[Depends(llm_limit)])
def global_search(query: str = Query(min_length=1, max_length=500),
                  _user=Depends(get_current_user)):
    return get_graph_service().global_answer(query)
