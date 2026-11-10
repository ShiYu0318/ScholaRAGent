"""共用測試工具：離線用的 FakeEmbedder 與資料路徑隔離。"""
import hashlib
import os

# 必須在 import src.config 之前執行：config 會載入 backend/.env，但不覆蓋已存在的
# 環境變數。這裡先放入假值，測試就拿不到真實金鑰；LLM 端點指向本機關閉的連接埠，
# 漏了替身的測試會立刻連線失敗，而不是悄悄用真實金鑰打外部服務。
_ISOLATED_ENV = {
    "GROQ_API_KEY": "test-key-not-real",
    "GROQ_BASE_URL": "http://127.0.0.1:9/v1",
    "APP_ENV": "development",
    "JWT_SECRET": "",
    "SCHEDULER_ENABLED": "0",
    "STORE_BACKEND": "sqlite",
    "DATABASE_URL": "",
    "TRUST_PROXY": "0",
    "RATE_LIMIT_ENABLED": "1",
}
for _name in ("DISCORD_BOT_TOKEN", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "SMTP_HOST",
              "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM", "EMAIL_TO", "LINE_CHANNEL_TOKEN",
              "LINE_TO", "GITHUB_TOKEN", "X_BEARER_TOKEN", "GOOGLE_CLIENT_ID",
              "GOOGLE_CLIENT_SECRET", "GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET",
              "DISCORD_CLIENT_ID", "DISCORD_CLIENT_SECRET"):
    _ISOLATED_ENV[_name] = ""
os.environ.update(_ISOLATED_ENV)

import numpy as np  # noqa: E402
import pytest  # noqa: E402


def _stable_hash(token):
    """跨 process 穩定的雜湊（內建 hash() 受 PYTHONHASHSEED 影響會使測試不穩）。"""
    return int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)


class FakeEmbedder:
    """不需下載模型的假 embedder：以詞袋雜湊產生正規化向量，具決定性。"""

    def __init__(self, dim=64):
        self.dim = dim

    def encode(self, texts):
        vecs = []
        for text in texts:
            v = np.zeros(self.dim, dtype="float32")
            for tok in str(text).lower().split():
                v[_stable_hash(tok) % self.dim] += 1.0
            norm = np.linalg.norm(v)
            if norm > 0:
                v /= norm
            vecs.append(v)
        return np.asarray(vecs, dtype="float32")


@pytest.fixture
def fake_embedder():
    return FakeEmbedder()


@pytest.fixture
def isolated_data(tmp_path, monkeypatch):
    """把 config 的資料檔路徑指到 tmp，避免測試污染真正的 data/。"""
    from src import config

    monkeypatch.setattr(config, "INDEX_PATH", tmp_path / "faiss.index")
    monkeypatch.setattr(config, "METADATA_PATH", tmp_path / "metadata.json")
    monkeypatch.setattr(config, "SCHEDULE_PATH", tmp_path / "schedule.json")
    return tmp_path


def make_paper(pid, title, abstract="", **extra):
    paper = {
        "id": pid,
        "title": title,
        "abstract": abstract or title,
        "authors": "A. Author",
        "link": f"https://arxiv.org/abs/{pid}",
        "published": "2026-01-01",
    }
    paper.update(extra)
    return paper

