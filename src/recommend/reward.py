"""偏好獎勵模型（Week14 升級）：從使用者互動的成對偏好學習各 action 權重。

概念貼近 RLHF 的獎勵建模：以「使用者對 A 的偏好大於 B」的成對比較，
用 logistic（Bradley–Terry）線上更新權重，讓學到的權重取代 ranker 的固定權重。
特徵為各 action 的（加權）次數向量。
"""
import numpy as np

from src.utils.logger import get_logger

# 特徵順序（各 action 的計數）
DEFAULT_ACTIONS = ("click", "like", "subscribe", "share", "rate", "ask", "dwell")


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


class PreferenceRewardModel:
    def __init__(self, actions=DEFAULT_ACTIONS, init=1.0, l2=0.0):
        self.logger = get_logger(self.__class__.__name__)
        self.actions = list(actions)
        self.index = {a: i for i, a in enumerate(self.actions)}
        self.weights = np.full(len(self.actions), float(init), dtype="float64")
        self.l2 = l2

    def _vec(self, features):
        v = np.zeros(len(self.actions), dtype="float64")
        for a, c in (features or {}).items():
            if a in self.index:
                v[self.index[a]] = float(c)
        return v

    def score(self, features):
        """給一組互動特徵打分（越高越該被推薦）。"""
        return float(self.weights @ self._vec(features))

    def update_pair(self, preferred, other, lr=0.1):
        """一次成對更新：讓 preferred 的分數高於 other。回傳這步的 loss。"""
        vp, vo = self._vec(preferred), self._vec(other)
        diff = self.weights @ (vp - vo)
        # 目標 P(preferred≻other)=sigmoid(diff)→1；梯度上升
        grad = _sigmoid(-diff)
        self.weights += lr * (grad * (vp - vo) - self.l2 * self.weights)
        return -np.log(_sigmoid(diff) + 1e-9)

    def fit(self, pairs, epochs=200, lr=0.1):
        """pairs：[(preferred_features, other_features), ...]。回傳最後一輪平均 loss。"""
        last = 0.0
        for _ in range(epochs):
            losses = [self.update_pair(p, o, lr=lr) for p, o in pairs]
            last = float(np.mean(losses)) if losses else 0.0
        return last

    def as_weights(self):
        """回傳 {action: weight}，可直接給 ranker.weighted_interaction_score 使用。"""
        return {a: float(self.weights[i]) for i, a in enumerate(self.actions)}


def learn_action_weights(pairs, actions=DEFAULT_ACTIONS, epochs=200, lr=0.1):
    """便利函式：從成對偏好學出 action 權重字典。"""
    model = PreferenceRewardModel(actions=actions)
    model.fit(pairs, epochs=epochs, lr=lr)
    return model.as_weights()
