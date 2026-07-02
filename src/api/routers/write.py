"""寫作端點：潤稿、貢獻抽取、審稿清單、LaTeX 草稿、簡報大綱、審閱建議。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.deps import get_current_user
from src.api.services.research import get_research_service

router = APIRouter(prefix="/api/write", tags=["write"])

TOOLS = ("polish", "contributions", "checklist", "latex", "slides", "review")


class WriteBody(BaseModel):
    text: str = Field(default="", max_length=20000)
    topic: str = Field(default="", max_length=500)


@router.post("/{tool}")
def write_tool(tool: str, body: WriteBody, _user=Depends(get_current_user)):
    if tool not in TOOLS:
        raise HTTPException(status_code=404, detail=f"未知寫作工具：{tool}")
    if not body.text.strip() and not body.topic.strip():
        raise HTTPException(status_code=422, detail="需提供 text 或 topic")
    content = get_research_service().write(tool, text=body.text, topic=body.topic)
    return {"content": content}
