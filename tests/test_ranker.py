"""ranker：互動 + 新鮮度排序、reward 加權。"""
from datetime import date

from src.recommend import ranker
from tests.conftest import make_paper


def test_interaction_boosts_ranking():
    papers = [make_paper("1", "A", published="2026-01-01"),
              make_paper("2", "B", published="2026-01-01")]
    ranked = ranker.rank_papers(papers, interaction_counts={"2": 10.0},
                                w_recency=0.0, today=date(2026, 1, 2))
    assert ranked[0]["id"] == "2"  # 有互動的排前面


def test_recency_boosts_ranking():
    papers = [make_paper("1", "old", published="2026-01-01"),
              make_paper("2", "new", published="2026-03-01")]
    ranked = ranker.rank_papers(papers, w_interaction=0.0, today=date(2026, 3, 2))
    assert ranked[0]["id"] == "2"


def test_stable_when_no_signal():
    papers = [make_paper("1", "A", published=""), make_paper("2", "B", published="")]
    ranked = ranker.rank_papers(papers, today=date(2026, 3, 2))
    assert [p["id"] for p in ranked] == ["1", "2"]  # 保持原順序


def test_weighted_interaction_score():
    score = ranker.weighted_interaction_score({"like": 2, "click": 1})
    # like=3*2 + click=1*1 = 7
    assert score == 7.0


def test_recency_score_bounds():
    assert ranker._recency_score("") == 0.0
    fresh = ranker._recency_score("2026-03-02", today=date(2026, 3, 2))
    assert fresh == 1.0
