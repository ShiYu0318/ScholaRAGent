"""SchedulerManager 單元測試：每人排程、勿擾、提醒輪詢、摘要去重（離線）。"""
from datetime import datetime, timedelta

import pytest

from src.api.services import library as library_module
from src.api.services.library import LibraryService
from src.scheduler import SchedulerManager
from src.store.sqlite_faiss import SqliteFaissStore


@pytest.fixture
def store(tmp_path, fake_embedder, isolated_data):
    s = SqliteFaissStore(db_path=tmp_path / "sched.db", embedder=fake_embedder)
    yield s
    s.close()


@pytest.fixture
def sent():
    return []


@pytest.fixture
def manager(store, sent):
    def fake_broadcast(text, channels):
        sent.append((text, channels))
        return {"fake": True}

    m = SchedulerManager(store=store, broadcast=fake_broadcast)
    yield m
    m.stop()


def test_schedule_all_creates_per_user_jobs(store, manager):
    u1 = store.create_user("a@b.c")
    u2 = store.create_user("b@b.c")
    store.set_notification_prefs(u2["id"], frequency="off")
    manager.start()
    jobs = {j["id"] for j in manager.status()["jobs"]}
    assert "reminders" in jobs
    assert f"digest:{u1['id']}" in jobs
    assert f"digest:{u2['id']}" not in jobs


def test_schedule_user_reacts_to_pref_change(store, manager):
    user = store.create_user("a@b.c")
    manager.start()
    job_id = f"digest:{user['id']}"
    assert job_id in {j["id"] for j in manager.status()["jobs"]}
    store.set_notification_prefs(user["id"], frequency="off")
    manager.schedule_user(user["id"])
    assert job_id not in {j["id"] for j in manager.status()["jobs"]}


def test_tick_reminders_fires_once(store, manager, sent):
    user = store.create_user("a@b.c")
    past = (datetime.now() - timedelta(minutes=5)).isoformat(timespec="seconds")
    r = store.add_reminder(user["id"], "到期提醒", past)
    fired = manager.tick_reminders()
    assert fired == [r["id"]]
    assert len(sent) == 1 and "到期提醒" in sent[0][0]
    # 同一提醒不重複推播
    assert manager.tick_reminders() == []
    assert len(sent) == 1


def test_send_digest_dedupes_across_runs(store, manager, sent, fake_embedder):
    user = store.create_user("a@b.c")
    store.set_notification_prefs(user["id"], channels=["telegram"])
    store.upsert_papers([
        {"id": "p1", "title": "Paper One", "abstract": "x", "authors": "",
         "link": "http://x/1", "published": "2026-07-01", "source": "arxiv"},
        {"id": "p2", "title": "Paper Two", "abstract": "y", "authors": "",
         "link": "http://x/2", "published": "2026-07-02", "source": "arxiv"},
    ])
    prev = library_module.set_library_service(
        LibraryService(store, embedder=fake_embedder))
    try:
        assert manager.send_digest(user["id"]) is not None
        assert len(sent) == 1 and "Paper One" in sent[0][0]
        # dedupe 開啟（預設）：同批論文不再推
        assert manager.send_digest(user["id"]) is None
    finally:
        library_module.set_library_service(prev)


def test_quiet_hours_crossing_midnight(store, manager):
    prefs = {"quiet_start": 22, "quiet_end": 7}
    assert manager._in_quiet(prefs, now=datetime(2026, 1, 1, 23)) is True
    assert manager._in_quiet(prefs, now=datetime(2026, 1, 1, 3)) is True
    assert manager._in_quiet(prefs, now=datetime(2026, 1, 1, 12)) is False
    assert manager._in_quiet({"quiet_start": None, "quiet_end": None}) is False
