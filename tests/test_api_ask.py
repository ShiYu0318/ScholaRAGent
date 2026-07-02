"""問答 SSE 與對話端點：離線（stub 檢索與 LLM 串流）。"""
import json

import pytest
from fastapi.testclient import TestClient

from src import store as store_module
from src.api.services import ask as ask_module
from src.store.sqlite_faiss import SqliteFaissStore

PAPERS = [
    {"id": "p1", "title": "GraphRAG Survey", "link": "http://x/1",
     "published": "2026-01-01", "authors": "A"},
    {"id": "p2", "title": "Adaptive RAG", "link": "http://x/2",
     "published": "2026-02-01", "authors": "B"},
]


class StubAskService:
    """不打網路：固定檢索結果 + 兩段式串流。"""

    def retrieve(self, question, k=4):
        return PAPERS

    citations = staticmethod(ask_module.AskService.citations)

    def stream(self, question, papers):
        yield "答案"
        yield "第二段"


@pytest.fixture
def api(tmp_path, fake_embedder):
    from src.api.app import create_app

    store = SqliteFaissStore(db_path=tmp_path / "api.db", embedder=fake_embedder)
    store.upsert_papers(PAPERS)  # 引用互動有 FK：論文須先入庫
    prev_store = store_module.set_store(store)
    prev_service = ask_module.set_ask_service(StubAskService())
    client = TestClient(create_app())
    yield client
    ask_module.set_ask_service(prev_service)
    store_module.set_store(prev_store)
    store.close()


@pytest.fixture
def auth(api):
    token = api.post("/auth/register",
                     json={"email": "a@b.c", "password": "password123"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def _events(resp):
    return [json.loads(line[len("data: "):])
            for line in resp.text.splitlines() if line.startswith("data: ")]


def test_ask_streams_tokens_citations_done(api, auth):
    resp = api.post("/api/ask", json={"question": "GraphRAG 是什麼？"}, headers=auth)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    events = _events(resp)
    types = [e["type"] for e in events]
    assert types == ["conversation", "token", "token", "citations", "done"]
    assert "".join(e["text"] for e in events if e["type"] == "token") == "答案第二段"
    assert [c["id"] for c in events[-2]["citations"]] == ["p1", "p2"]


def test_ask_persists_conversation_and_interactions(api, auth):
    resp = api.post("/api/ask", json={"question": "什麼是 Adaptive RAG？"}, headers=auth)
    conv_id = _events(resp)[0]["conversation_id"]

    conv = api.get(f"/api/conversations/{conv_id}", headers=auth).json()
    assert conv["title"].startswith("什麼是 Adaptive RAG")
    assert [m["role"] for m in conv["messages"]] == ["user", "assistant"]
    assert conv["messages"][1]["content"] == "答案第二段"
    assert len(conv["messages"][1]["citations"]) == 2

    store = store_module.get_store()
    assert store.action_totals()["ask"] == 2  # 兩篇引用論文各記一筆


def test_ask_continues_existing_conversation(api, auth):
    first = _events(api.post("/api/ask", json={"question": "Q1"}, headers=auth))
    conv_id = first[0]["conversation_id"]
    api.post("/api/ask", json={"question": "Q2", "conversation_id": conv_id}, headers=auth)
    conv = api.get(f"/api/conversations/{conv_id}", headers=auth).json()
    assert [m["role"] for m in conv["messages"]] == ["user", "assistant", "user", "assistant"]


def test_ask_rejects_foreign_conversation(api, auth):
    conv_id = _events(api.post("/api/ask", json={"question": "Q"}, headers=auth))[0]["conversation_id"]
    other = api.post("/auth/register",
                     json={"email": "o@b.c", "password": "password123"}).json()["token"]
    resp = api.post("/api/ask", json={"question": "Q", "conversation_id": conv_id},
                    headers={"Authorization": f"Bearer {other}"})
    assert resp.status_code == 404


def test_ask_requires_auth(api):
    assert api.post("/api/ask", json={"question": "Q"}).status_code == 401


def test_conversations_list_search_rename_delete(api, auth):
    api.post("/api/ask", json={"question": "GraphRAG 全域搜尋"}, headers=auth)
    api.post("/api/ask", json={"question": "diffusion 模型"}, headers=auth)

    items = api.get("/api/conversations", headers=auth).json()["items"]
    assert len(items) == 2
    hits = api.get("/api/conversations", params={"query": "GraphRAG"}, headers=auth).json()["items"]
    assert len(hits) == 1

    conv_id = hits[0]["id"]
    renamed = api.patch(f"/api/conversations/{conv_id}", json={"title": "圖譜討論"},
                        headers=auth).json()
    assert renamed["title"] == "圖譜討論"

    assert api.delete(f"/api/conversations/{conv_id}", headers=auth).status_code == 204
    assert api.get(f"/api/conversations/{conv_id}", headers=auth).status_code == 404


def test_share_and_public_read(api, auth):
    conv_id = _events(api.post("/api/ask", json={"question": "分享測試"}, headers=auth))[0]["conversation_id"]
    share = api.post(f"/api/conversations/{conv_id}/share", headers=auth).json()
    assert share["token"] in share["url"]

    public = api.get(f"/api/shared/{share['token']}")  # 不帶 token
    assert public.status_code == 200
    body = public.json()
    assert body["title"].startswith("分享測試")
    assert [m["role"] for m in body["messages"]] == ["user", "assistant"]
    assert "user_id" not in body

    assert api.get("/api/shared/bogus-token").status_code == 404
