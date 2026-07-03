"""LSTM 滑動視窗時序預測器。

以 torch 訓練一個小型 LSTM，從關鍵字熱度序列預測下一期。序列過短時
自動回退為移動平均，避免訓練不穩。刻意保持模型小、epoch 少，讓推論快、可離線測試。
"""
import numpy as np
import torch
import torch.nn as nn

from src.utils.logger import get_logger


class _LSTMNet(nn.Module):
    def __init__(self, hidden=16):
        super().__init__()
        self.lstm = nn.LSTM(input_size=1, hidden_size=hidden, batch_first=True)
        self.fc = nn.Linear(hidden, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])


class LSTMForecaster:
    def __init__(self, window=4, hidden=16, epochs=200, lr=0.01, seed=0):
        self.logger = get_logger(self.__class__.__name__)
        self.window = window
        self.hidden = hidden
        self.epochs = epochs
        self.lr = lr
        self.seed = seed
        self.net = None
        self._fallback = None      # 短序列時的回退值
        self._lo = 0.0
        self._span = 1.0
        self._series = []

    def _normalize(self, series):
        arr = np.asarray(series, dtype="float32")
        self._lo = float(arr.min())
        self._span = float(arr.max() - arr.min()) or 1.0
        return (arr - self._lo) / self._span

    def _denormalize(self, value):
        return float(value) * self._span + self._lo

    def fit(self, series):
        series = [float(x) for x in series]
        self._series = series
        # 需要至少 window+1 個點才組得出一組訓練樣本；再多幾組才值得訓練
        if len(series) < self.window + 2:
            tail = series[-self.window:] if series else [0.0]
            self._fallback = sum(tail) / len(tail)
            return self

        torch.manual_seed(self.seed)
        norm = self._normalize(series)
        xs, ys = [], []
        for i in range(len(norm) - self.window):
            xs.append(norm[i:i + self.window])
            ys.append(norm[i + self.window])
        X = torch.tensor(np.array(xs), dtype=torch.float32).unsqueeze(-1)  # (N, window, 1)
        y = torch.tensor(np.array(ys), dtype=torch.float32).unsqueeze(-1)  # (N, 1)

        self.net = _LSTMNet(self.hidden)
        opt = torch.optim.Adam(self.net.parameters(), lr=self.lr)
        loss_fn = nn.MSELoss()
        self.net.train()
        for _ in range(self.epochs):
            opt.zero_grad()
            pred = self.net(X)
            loss = loss_fn(pred, y)
            loss.backward()
            opt.step()
        return self

    def predict(self, steps=1):
        """預測未來 steps 期，回傳非負數值清單。"""
        if self.net is None:
            return [max(0.0, self._fallback if self._fallback is not None else 0.0)] * steps

        self.net.eval()
        norm = list(self._normalize(self._series))
        preds = []
        with torch.no_grad():
            for _ in range(steps):
                window = torch.tensor(
                    np.array(norm[-self.window:]), dtype=torch.float32
                ).reshape(1, self.window, 1)
                nxt = float(self.net(window).item())
                norm.append(nxt)
                preds.append(max(0.0, self._denormalize(nxt)))
        return preds

    def forecast_next(self, series):
        """便利方法：fit 後回傳下一期單一預測值。"""
        return self.fit(series).predict(1)[0]
