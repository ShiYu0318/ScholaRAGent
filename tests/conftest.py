"""共用測試工具：離線用的 FakeEmbedder 與資料路徑隔離。"""
import hashlib

import numpy as np
import pytest


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
