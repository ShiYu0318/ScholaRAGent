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

    def __init__(self):
        self.calls = []

    def retrieve(self, question, k=4, paper_ids=None):
        self.calls.append({"query": question, "paper_ids": paper_ids})
        if paper_ids is not None:
            return [p for p in PAPERS if p["id"] in paper_ids]
        return PAPERS

    citations = staticmethod(ask_module.AskService.citations)
    retrieval_query = staticmethod(ask_module.AskService.retrieval_query)

    def stream(self, question, papers, history=None):
        self.calls[-1]["history"] = history
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


def test_stream_errors_do_not_leak_exception_details(api, auth):
    class Boom(StubAskService):
        def retrieve(self, question, k=4, paper_ids=None):
            raise RuntimeError("postgresql://air:s3cret@db:5432 connection refused")

    prev = ask_module.set_ask_service(Boom())
    try:
        resp = api.post("/api/ask", json={"question": "what?"}, headers=auth)
    finally:
        ask_module.set_ask_service(prev)
    assert "s3cret" not in resp.text and "postgresql" not in resp.text
    assert '"type": "error"' in resp.text


def test_generation_errors_do_not_leak_exception_details(api, auth):
    class Boom(StubAskService):
        def stream(self, question, papers, history=None):
            yield "部分"
            raise RuntimeError("Authorization: Bearer gsk_live_secret")

    prev = ask_module.set_ask_service(Boom())
    try:
        resp = api.post("/api/ask", json={"question": "what?"}, headers=auth)
    finally:
        ask_module.set_ask_service(prev)
    assert "gsk_live_secret" not in resp.text


def test_share_can_be_revoked(api, auth):
    api.post("/api/ask", json={"question": "what?"}, headers=auth)
    conv_id = api.get("/api/conversations", headers=auth).json()["items"][0]["id"]
    token = api.post(f"/api/conversations/{conv_id}/share", headers=auth).json()["token"]
    assert api.get(f"/api/shared/{token}").status_code == 200

    assert api.delete(f"/api/conversations/{conv_id}/share", headers=auth).status_code == 204
    assert api.get(f"/api/shared/{token}").status_code == 404
    # 重新分享會拿到不同的 token，舊連結不會復活
    new = api.post(f"/api/conversations/{conv_id}/share", headers=auth).json()["token"]
    assert new != token
    assert api.get(f"/api/shared/{token}").status_code == 404


def test_cannot_revoke_someone_elses_share(api, auth):
    api.post("/api/ask", json={"question": "what?"}, headers=auth)
    conv_id = api.get("/api/conversations", headers=auth).json()["items"][0]["id"]
    token = api.post(f"/api/conversations/{conv_id}/share", headers=auth).json()["token"]
    other = api.post("/auth/register",
                     json={"email": "o@b.c", "password": "password123"}).json()["token"]
    resp = api.delete(f"/api/conversations/{conv_id}/share",
                      headers={"Authorization": f"Bearer {other}"})
    assert resp.status_code == 404
    assert api.get(f"/api/shared/{token}").status_code == 200


# ---- 檢索範圍與對話脈絡 ----
def _service():
    return ask_module.get_ask_service()


def test_ask_scoped_to_explicit_papers(api, auth):
    resp = api.post("/api/ask", headers=auth, json={"question": "q", "paper_ids": ["p2"]})
    assert _service().calls[-1]["paper_ids"] == ["p2"]
    assert '"id": "p2"' in resp.text and '"id": "p1"' not in resp.text


def test_ask_scoped_to_project_and_followups_keep_the_scope(api, auth):
    project = api.post("/api/projects", headers=auth, json={"name": "P"}).json()
    api.post(f"/api/projects/{project['id']}/papers", headers=auth, json={"paper_ids": ["p1"]})
    api.post("/api/ask", headers=auth, json={"question": "第一題", "project_id": project["id"]})
    assert _service().calls[-1]["paper_ids"] == ["p1"]

    convs = api.get(f"/api/conversations?project_id={project['id']}", headers=auth).json()
    conv_id = convs["items"][0]["id"]
    # 追問不帶 project_id：沿用對話所屬專案
    api.post("/api/ask", headers=auth, json={"question": "那缺點呢", "conversation_id": conv_id})
    call = _service().calls[-1]
    assert call["paper_ids"] == ["p1"]
    assert call["query"] == "第一題 那缺點呢"
    assert [m["role"] for m in call["history"]] == ["user", "assistant"]
    assert api.get(f"/api/projects/{project['id']}", headers=auth).json()[
        "conversation_count"] == 1


def test_first_question_has_no_history_and_searches_whole_library(api, auth):
    api.post("/api/ask", headers=auth, json={"question": "what?"})
    call = _service().calls[-1]
    assert call["paper_ids"] is None and call["history"] == [] and call["query"] == "what?"


def test_ask_in_someone_elses_project_is_404(api, auth):
    other = api.post("/auth/register",
                     json={"email": "z@b.c", "password": "password123"}).json()["token"]
    project = api.post("/api/projects", json={"name": "theirs"},
                       headers={"Authorization": f"Bearer {other}"}).json()
    resp = api.post("/api/ask", headers=auth,
                    json={"question": "q", "project_id": project["id"]})
    assert resp.status_code == 404
    assert api.get("/api/conversations", headers=auth).json()["items"] == []


def test_scoped_search_only_returns_papers_in_scope(tmp_path, fake_embedder):
    store = SqliteFaissStore(db_path=tmp_path / "s.db", embedder=fake_embedder)
    papers = [{"id": f"s{i}", "title": f"graph retrieval {i}", "abstract": "graph retrieval",
               "link": f"https://e.com/{i}"} for i in range(6)]
    papers.append({"id": "far", "title": "protein folding", "abstract": "biology",
                   "link": "https://e.com/far"})
    store.upsert_papers(papers)
    store.index_papers(papers)
    service = ask_module.AskService(store)
    hits = service.retrieve("graph retrieval", k=3, paper_ids=["s1", "far"])
    assert {p["id"] for p in hits} == {"s1", "far"}      # 不足 k 篇時以範圍內論文補滿
    assert service.retrieve("graph retrieval", k=3, paper_ids=[]) == []
    assert len(service.retrieve("graph retrieval", k=2,
                                paper_ids=["s0", "s1", "s2", "s3"])) == 2
    store.close()
