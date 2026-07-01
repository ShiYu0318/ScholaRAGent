"""嵌入快取，離線。"""
import numpy as np

from src.rag.caching_embedder import CachingEmbedder
from tests.conftest import FakeEmbedder


class TrackingEmbedder(FakeEmbedder):
    def __init__(self):
        super().__init__(dim=8)
        self.seen = []

    def encode(self, texts):
        self.seen += list(texts)
        return super().encode(texts)


def test_only_encodes_uncached_texts():
    base = TrackingEmbedder()
    ce = CachingEmbedder(base)
    ce.encode(["a", "b"])
    ce.encode(["a", "c"])
    assert base.seen == ["a", "b", "c"]      # a 不會重算


def test_output_matches_base_and_order():
    base = TrackingEmbedder()
    ce = CachingEmbedder(base)
    out = ce.encode(["a", "b"])
    assert np.allclose(out, FakeEmbedder(dim=8).encode(["a", "b"]))


def test_dim_passthrough():
    assert CachingEmbedder(FakeEmbedder(dim=8)).dim == 8
