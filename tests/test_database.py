"""Database（SQLite）：論文 upsert/去重、互動記錄與統計。"""
import pytest

from src.db.database import Database
from tests.conftest import make_paper


@pytest.fixture
def db(tmp_path):
    d = Database(path=tmp_path / "test.db")
    yield d
    d.close()


def test_upsert_new_and_dup(db):
    assert db.upsert_paper(make_paper("1", "Paper One")) is True
    assert db.upsert_paper(make_paper("1", "Paper One v2")) is False  # 已存在
    assert db.count_papers() == 1
    assert db.get_paper("1")["title"] == "Paper One v2"  # 更新標題


def test_upsert_papers_batch(db):
    n = db.upsert_papers([make_paper("1", "A"), make_paper("2", "B"), make_paper("1", "A")])
    assert n == 2  # 只有兩個是新的
    assert db.count_papers() == 2


def test_summary_not_overwritten_by_null(db):
    db.upsert_paper(make_paper("1", "A", summary="重要摘要"))
    db.upsert_paper(make_paper("1", "A"))  # 無 summary，不應清掉舊摘要
    assert db.get_paper("1")["summary"] == "重要摘要"


def test_all_papers_filter_source(db):
    db.upsert_paper(make_paper("1", "arxiv paper", source="arxiv"))
    db.upsert_paper(make_paper("2", "hn post", source="hackernews"))
    hn = db.all_papers(source="hackernews")
    assert [p["id"] for p in hn] == ["2"]


def test_log_and_count_interactions(db):
    db.upsert_paper(make_paper("1", "A"))
    db.log_interaction("click", paper_id="1", user_id=42)
    db.log_interaction("like", paper_id="1", user_id=42, value=2.0)
    db.log_interaction("click", paper_id="1", user_id=7)
    counts = db.interaction_counts()
    assert counts["1"] == pytest.approx(4.0)  # 1 + 2 + 1
    like_only = db.interaction_counts(action="like")
    assert like_only["1"] == pytest.approx(2.0)


def test_action_totals(db):
    db.log_interaction("click")
    db.log_interaction("click")
    db.log_interaction("share")
    assert db.action_totals() == {"click": 2, "share": 1}
