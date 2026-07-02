"""問答端點：SSE 逐字串流，末端補引用，並持久化對話。"""
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.api.deps import get_current_user, get_store
from src.api.services.ask import get_ask_service
from src.store.base import Store

router = APIRouter(prefix="/api", tags=["ask"])


class AskBody(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    conversation_id: int | None = None
    k: int = Field(default=4, ge=1, le=20)


def sse(payload):
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/ask")
def ask(body: AskBody, user=Depends(get_current_user), store: Store = Depends(get_store)):
    service = get_ask_service()
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="問題不可為空")

    conv = None
    if body.conversation_id is not None:
        conv = store.get_conversation(body.conversation_id, user_id=user["id"])
        if conv is None:
            raise HTTPException(status_code=404, detail="對話不存在")
    if conv is None:
        conv = store.create_conversation(user["id"], title=question[:80])
    store.add_message(conv["id"], "user", question)

    def gen():
        yield sse({"type": "conversation", "conversation_id": conv["id"]})
        try:
            papers = service.retrieve(question, k=body.k)
        except Exception as e:
            yield sse({"type": "error", "message": f"檢索失敗：{e}"})
            return

        parts = []
        try:
            for delta in service.stream(question, papers):
                parts.append(delta)
                yield sse({"type": "token", "text": delta})
        except Exception as e:
            yield sse({"type": "error", "message": f"生成失敗：{e}"})

        citations = service.citations(papers)
        message = store.add_message(conv["id"], "assistant", "".join(parts),
                                    citations=citations)
        for p in papers:
            try:
                store.log_interaction("ask", paper_id=p.get("id"), user_id=user["id"])
            except Exception:
                pass  # 互動記錄失敗（如論文未入庫）不影響回答本身
        if citations:
            yield sse({"type": "citations", "citations": citations})
        yield sse({"type": "done", "conversation_id": conv["id"],
                   "message_id": message["id"]})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
