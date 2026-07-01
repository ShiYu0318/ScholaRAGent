"""LSTMForecaster：短序列回退、可訓練並產出合理預測（固定 seed，少 epoch）。"""
import math

from src.analysis.lstm_forecaster import LSTMForecaster
from src.analysis import trends


def test_short_series_falls_back():
    f = LSTMForecaster(window=4)
    # 少於 window+2 個點 -> 回退移動平均，不訓練
    out = f.forecast_next([1, 2, 3])
    assert f.net is None
    assert out >= 0.0


def test_predict_returns_finite_nonnegative():
    series = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    f = LSTMForecaster(window=4, epochs=80, seed=0)
    out = f.forecast_next(series)
    assert math.isfinite(out)
    assert out >= 0.0


def test_predict_multiple_steps():
    series = [2, 4, 6, 8, 10, 12, 14, 16]
    f = LSTMForecaster(window=3, epochs=80, seed=0)
    f.fit(series)
    preds = f.predict(steps=3)
    assert len(preds) == 3
    assert all(p >= 0.0 and math.isfinite(p) for p in preds)


def test_constant_series_predicts_constant():
    f = LSTMForecaster(window=3, epochs=50, seed=0)
    out = f.forecast_next([5, 5, 5, 5, 5, 5, 5])
    # 常數序列 span=0，正規化後為常數，預測應貼近 5
    assert abs(out - 5.0) < 1.0


def test_trends_forecast_lstm_method():
    out = trends.forecast([1, 2, 3, 4, 5, 6, 7, 8], method="lstm", window=3)
    assert out >= 0.0
    assert math.isfinite(out)
