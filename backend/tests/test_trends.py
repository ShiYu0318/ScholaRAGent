"""trends：關鍵字抽取、時序、預測、上升關鍵字。"""
import pytest

from src.analysis import trends
from tests.conftest import make_paper


def _papers():
    return [
        make_paper("1", "transformer for vision", "transformer attention", published="2026-01-15"),
        make_paper("2", "transformer scaling", "transformer large", published="2026-02-10"),
        make_paper("3", "diffusion model image", "diffusion generative", published="2026-02-20"),
        make_paper("4", "transformer agents", "transformer planning", published="2026-03-05"),
    ]


def test_extract_keywords_filters_stopwords():
    kws = dict(trends.extract_keywords(_papers(), top_n=10))
    assert "transformer" in kws
    assert kws["transformer"] == 3
    # 停用詞不應出現
    assert "the" not in kws and "for" not in kws


def test_keyword_timeseries_sorted():
    periods, counts = trends.keyword_timeseries(_papers(), "transformer")
    assert periods == ["2026-01", "2026-02", "2026-03"]
    assert counts == [1, 1, 1]


def test_forecast_moving_average():
    assert trends.forecast([2, 4, 6], method="moving_average", window=3) == 4.0
    assert trends.forecast([], method="moving_average") == 0.0


def test_forecast_linear_extrapolates():
    # 完美遞增序列，線性外推下一期應約為 4
    out = trends.forecast([0, 1, 2, 3], method="linear")
    assert out == pytest.approx(4.0)


def test_forecast_non_negative():
    out = trends.forecast([5, 3, 1], method="linear")
    assert out >= 0.0


def test_trending_keywords_detects_rising():
    papers = _papers() + [
        make_paper("5", "transformer robotics", "transformer control", published="2026-03-20"),
        make_paper("6", "transformer speech", "transformer audio", published="2026-03-25"),
    ]
    rising = dict(trends.trending_keywords(papers, top_n=10))
    assert "transformer" in rising
    assert rising["transformer"] > 0
