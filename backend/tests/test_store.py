"""Store 抽象層行為測試：同一套規格跑 SQLite+FAISS 與 Postgres+pgvector。

Postgres 後端需要 TEST_DATABASE_URL（pgvector 已裝的資料庫）；未設定時
自動 skip，CI 以 service container 提供。
"""
import os

import pytest

from src.store.sqlite_faiss import SqliteFaissStore

_PG_URL = os.getenv("TEST_DATABASE_URL", "")

# 依外鍵順序 TRUNCATE，保每測試隔離
_PG_TABLES = ("paper_embeddings", "interactions", "messages", "conversations",
              "reading_list", "notification_preferences", "reminders",
              "learning_paths", "user_skills", "feeds", "user_subscriptions",
              "papers", "users")


@pytest.fixture(params=[
    "sqlite",
    pytest.param("postgres", marks=pytest.mark.skipif(
        not _PG_URL, reason="TEST_DATABASE_URL 未設定")),
])
def store(request, tmp_path, fake_embedder):
    if request.param == "postgres":
        from src.store.postgres_pgvector import PostgresPgvectorStore
        s = PostgresPgvectorStore(dsn=_PG_URL, embedder=fake_embedder)
        for table in _PG_TABLES:
            s._conn.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
    else:
        s = SqliteFaissStore(db_path=tmp_path / "store.db", embedder=fake_embedder)
    yield s
    s.close()


def test_create_and_get_user(store):
    user = store.create_user("Alice@Example.com", password_hash="h", display_name="Alice")
    assert user["email"] == "alice@example.com"
    assert store.get_user(user["id"])["display_name"] == "Alice"
    assert store.get_user_by_email("ALICE@example.COM")["id"] == user["id"]


def test_duplicate_email_raises(store):
    store.create_user("a@b.c")
    with pytest.raises(ValueError):
        store.create_user("a@b.c")


def test_oauth_lookup_and_update(store):
    user = store.create_user("o@b.c", google_sub="g-123")
    assert store.get_user_by_oauth("google_sub", "g-123")["id"] == user["id"]
    store.update_user(user["id"], discord_id="d-9", display_name="O")
    updated = store.get_user(user["id"])
    assert updated["discord_id"] == "d-9" and updated["display_name"] == "O"
    with pytest.raises(ValueError):
        store.get_user_by_oauth("email", "x")  # 不允許任意欄位查詢


def test_papers_and_interactions(store):
    n = store.upsert_papers([
        {"id": "p1", "title": "T1", "abstract": "A"},
        {"id": "p2", "title": "T2", "abstract": "B"},
    ])
    assert n == 2 and store.count_papers() == 2
    assert store.get_paper("p1")["title"] == "T1"
    store.log_interaction("like", paper_id="p1", user_id=7)
    store.log_interaction("click", paper_id="p1", user_id=7)
    assert store.interaction_counts()["p1"] == 2.0
    assert store.action_totals(user_id=7) == {"like": 1, "click": 1}
    assert len(store.user_interactions(7)) == 2


def test_vector_index_and_search(store, isolated_data):
    papers = [
        {"id": "v1", "title": "graph neural networks", "abstract": "GNN message passing"},
        {"id": "v2", "title": "diffusion models", "abstract": "image generation"},
    ]
    added = store.index_papers(papers)
    assert len(added) == 2
    top = store.search("graph neural networks", k=1)
    assert top[0]["id"] == "v1"


def test_feeds_crud(store):
    u = store.create_user("f@b.c")
    feed = store.add_feed(u["id"], "https://example.com/rss", title="Ex")
    assert feed["enabled"] is True
    with pytest.raises(ValueError):
        store.add_feed(u["id"], "https://example.com/rss")
    assert len(store.list_feeds(u["id"])) == 1
    updated = store.update_feed(feed["id"], u["id"], enabled=False, title="Ex2")
    assert updated["enabled"] is False and updated["title"] == "Ex2"
    assert store.update_feed(feed["id"], u["id"] + 99, title="x") is None  # 非本人
    assert store.delete_feed(feed["id"], u["id"]) is True
    assert store.list_feeds(u["id"]) == []


def test_subscriptions(store):
    u = store.create_user("s@b.c")
    store.add_subscription(u["id"], "gnn", ["Graph", "GNN"])
    subs = store.list_subscriptions(u["id"])
    assert subs == [{"name": "gnn", "keywords": ["graph", "gnn"]}]
    store.add_subscription(u["id"], "gnn", ["message passing"])  # 覆蓋
    assert store.list_subscriptions(u["id"])[0]["keywords"] == ["message passing"]
    assert store.remove_subscription(u["id"], "gnn") is True
    assert store.remove_subscription(u["id"], "gnn") is False


def test_conversations_messages_share(store):
    u = store.create_user("c@b.c")
    conv = store.create_conversation(u["id"], title="RAG 問答")
    store.add_message(conv["id"], "user", "什麼是 GraphRAG？")
    store.add_message(conv["id"], "assistant", "GraphRAG 是……", citations=[{"id": "p1"}])
    got = store.get_conversation(conv["id"], user_id=u["id"])
    assert len(got["messages"]) == 2
    assert got["messages"][1]["citations"] == [{"id": "p1"}]
    assert store.get_conversation(conv["id"], user_id=u["id"] + 1) is None  # 擁有者檢查

    assert store.list_conversations(u["id"], query="GraphRAG")[0]["id"] == conv["id"]
    assert store.list_conversations(u["id"], query="不存在的詞") == []

    token = store.share_conversation(conv["id"], u["id"])
    assert token and store.share_conversation(conv["id"], u["id"]) == token  # 冪等
    shared = store.get_shared_conversation(token)
    assert shared["id"] == conv["id"] and len(shared["messages"]) == 2

    store.rename_conversation(conv["id"], u["id"], "新標題")
    assert store.get_conversation(conv["id"])["title"] == "新標題"
    assert store.delete_conversation(conv["id"], u["id"]) is True
    assert store.get_conversation(conv["id"]) is None


def test_reading_list(store):
    u = store.create_user("r@b.c")
    store.reading_upsert(u["id"], "p1", "Paper 1", tags=["gnn"])
    store.reading_upsert(u["id"], "p2", "Paper 2", state="reading")
    assert len(store.reading_items(u["id"])) == 2
    assert store.reading_items(u["id"], state="reading")[0]["id"] == "p2"
    assert store.reading_set_state(u["id"], "p1", "done") is True
    with pytest.raises(ValueError):
        store.reading_set_state(u["id"], "p1", "bogus")
    assert store.reading_remove(u["id"], "p1") is True
    assert len(store.reading_items(u["id"])) == 1


def test_notification_prefs_defaults_and_update(store):
    u = store.create_user("n@b.c")
    prefs = store.get_notification_prefs(u["id"])
    assert prefs["frequency"] == "daily" and prefs["channels"] == ["web"]
    updated = store.set_notification_prefs(u["id"], frequency="weekly", hour=8,
                                           channels=["web", "discord"], dedupe=False)
    assert updated["frequency"] == "weekly"
    again = store.get_notification_prefs(u["id"])
    assert again["hour"] == 8 and again["dedupe"] is False
    assert again["channels"] == ["web", "discord"]


def test_reminders(store):
    u = store.create_user("rem@b.c")
    r = store.add_reminder(u["id"], "讀完 survey", "2026-01-01T00:00:00+00:00")
    assert store.list_reminders(u["id"])[0]["text"] == "讀完 survey"
    assert store.due_reminders("2026-06-01T00:00:00+00:00")[0]["id"] == r["id"]
    assert store.complete_reminder(r["id"], u["id"]) is True
    assert store.list_reminders(u["id"]) == []
    assert store.list_reminders(u["id"], include_done=True)[0]["done"] is True
    assert store.delete_reminder(r["id"], u["id"]) is True


def test_learning_paths_and_skills(store):
    u = store.create_user("l@b.c")
    path = store.create_learning_path(u["id"], "GraphRAG", [{"step": "讀 survey"}])
    assert path["items"][0]["step"] == "讀 survey" and path["progress"] == {}
    updated = store.update_learning_path(path["id"], u["id"], progress={"0": True})
    assert updated["progress"] == {"0": True}
    assert store.update_learning_path(path["id"], u["id"] + 1, topic="x") is None
    assert len(store.list_learning_paths(u["id"])) == 1
    assert store.delete_learning_path(path["id"], u["id"]) is True

    store.set_skill(u["id"], "rag", 60)
    store.set_skill(u["id"], "rag", 75)
    skills = store.list_skills(u["id"])
    assert len(skills) == 1 and skills[0]["level"] == 75.0


def test_stats(store):
    store.create_user("st@b.c")
    store.upsert_papers([{"id": "p1", "title": "T"}])
    s = store.stats()
    assert s["users"] == 1 and s["papers"] == 1
    assert s["backend"] in ("sqlite_faiss", "postgres_pgvector")
