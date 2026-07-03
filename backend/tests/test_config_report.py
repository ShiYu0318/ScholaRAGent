"""設定韌性檢查。"""
from types import SimpleNamespace

from src.config_report import config_report


def _cfg(**kw):
    base = dict(GROQ_API_KEY="", DISCORD_BOT_TOKEN="", DISCORD_CHANNEL_ID=0,
                TELEGRAM_BOT_TOKEN="", SMTP_HOST="", RERANK_ENABLED=False,
                X_BEARER_TOKEN="")
    base.update(kw)
    return SimpleNamespace(**base)


def test_missing_required_keys_reported():
    rep = config_report(_cfg())
    assert rep["ok"] is False
    assert "GROQ_API_KEY" in rep["missing_required"]
    assert "DISCORD_BOT_TOKEN" in rep["missing_required"]


def test_all_required_present_ok():
    rep = config_report(_cfg(GROQ_API_KEY="k", DISCORD_BOT_TOKEN="t", DISCORD_CHANNEL_ID=123))
    assert rep["ok"] is True
    assert rep["missing_required"] == []


def test_optional_feature_flags():
    rep = config_report(_cfg(TELEGRAM_BOT_TOKEN="x", RERANK_ENABLED=True))
    assert rep["features"]["telegram"] is True
    assert rep["features"]["reranker"] is True
    assert rep["features"]["email"] is False
