"""PreferenceRewardModel：成對偏好學習、權重收斂、與 ranker 整合。"""
from src.recommend.reward import PreferenceRewardModel, learn_action_weights
from src.recommend import ranker


def test_score_uses_weights():
    m = PreferenceRewardModel(actions=("click", "like"), init=1.0)
    assert m.score({"click": 2, "like": 3}) == 5.0


def test_learns_to_prefer_like_over_click():
    # 偏好樣本：使用者一致偏好「有 like」的論文，勝過「只有 click」的
    pairs = [({"like": 1}, {"click": 1})] * 30
    m = PreferenceRewardModel(actions=("click", "like"), init=1.0)
    loss_before = m.update_pair({"like": 1}, {"click": 1})  # 未訓練前
    m.fit(pairs, epochs=300, lr=0.2)
    w = m.as_weights()
    assert w["like"] > w["click"]                     # like 權重被學高
    assert m.score({"like": 1}) > m.score({"click": 1})
    # 訓練後對同一對的偏好更強（loss 更低）
    assert m.update_pair({"like": 1}, {"click": 1}) < loss_before


def test_fit_reduces_loss():
    pairs = [({"subscribe": 1}, {"click": 1})] * 20
    m = PreferenceRewardModel()
    first = m.fit(pairs, epochs=1, lr=0.1)
    later = m.fit(pairs, epochs=300, lr=0.1)
    assert later < first


def test_learn_action_weights_helper_feeds_ranker():
    pairs = [({"like": 1}, {"click": 1})] * 30
    weights = learn_action_weights(pairs, actions=("click", "like"), epochs=300, lr=0.2)
    # 學到的權重可直接餵給 ranker 的加權互動分數
    like_score = ranker.weighted_interaction_score({"like": 1}, weights=weights)
    click_score = ranker.weighted_interaction_score({"click": 1}, weights=weights)
    assert like_score > click_score
