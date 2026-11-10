"""測試行程不得持有真實金鑰，也不得能連到真實的 LLM 端點。"""
from src import config


def test_llm_credentials_are_placeholders():
    assert config.GROQ_API_KEY == "test-key-not-real"
    assert config.GROQ_BASE_URL.startswith("http://127.0.0.1:9")


def test_no_third_party_secrets_are_loaded():
    for name in ("DISCORD_BOT_TOKEN", "TELEGRAM_BOT_TOKEN", "SMTP_PASSWORD",
                 "LINE_CHANNEL_TOKEN", "GITHUB_TOKEN", "X_BEARER_TOKEN",
                 "GOOGLE_CLIENT_SECRET", "GITHUB_CLIENT_SECRET", "DISCORD_CLIENT_SECRET",
                 "JWT_SECRET", "DATABASE_URL"):
        assert getattr(config, name) == "", name
