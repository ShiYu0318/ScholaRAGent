"""MemoryStore：新增、動態過濾、壓縮、持久化。"""
import pytest

from src.memory.memory_store import MemoryStore


@pytest.fixture
def mem(tmp_path):
    return MemoryStore(path=str(tmp_path / "mem.json"), max_items=5, keep_recent=2)


def test_add_and_all(mem):
    mem.add("u1", "喜歡 multi-agent", kind="pref")
    mem.add("u1", "問過 RAG", kind="query")
    assert len(mem.all("u1")) == 2
    assert mem.all("u2") == []


def test_filter_by_kind_and_contains(mem):
    mem.add("u1", "喜歡 multi-agent RL", kind="pref")
    mem.add("u1", "喜歡 diffusion", kind="pref")
    mem.add("u1", "問過 memory", kind="query")
    assert len(mem.filter("u1", kind="pref")) == 2
    hits = mem.filter("u1", contains="diffusion")
    assert len(hits) == 1 and "diffusion" in hits[0]["content"]


def test_filter_limit_recent_first(mem):
    for i in range(4):
        mem.add("u1", f"note {i}", ts=f"2026-01-0{i+1}T00:00:00")
    recent = mem.filter("u1", limit=2)
    assert [m["content"] for m in recent] == ["note 3", "note 2"]


def test_compress_when_over_capacity(mem):
    for i in range(8):
        mem.add("u1", f"memory {i}", ts=f"2026-01-{i+1:02d}T00:00:00")
    called = {}

    def summarizer(texts):
        called["n"] = len(texts)
        return "壓縮摘要"

    assert mem.compress("u1", summarizer) is True
    items = mem.all("u1")
    # 保留 2 則原文 + 1 則摘要
    assert len(items) == 3
    assert any(m["kind"] == "summary" and m["content"] == "壓縮摘要" for m in items)
    assert called["n"] == 6  # 壓縮了較舊的 6 則


def test_compress_noop_when_small(mem):
    mem.add("u1", "only one")
    assert mem.compress("u1", lambda t: "x") is False


def test_persistence(tmp_path):
    path = str(tmp_path / "mem.json")
    m1 = MemoryStore(path=path)
    m1.add("u1", "記住我")
    m2 = MemoryStore(path=path)
    assert [x["content"] for x in m2.all("u1")] == ["記住我"]


def test_context_block(mem):
    mem.add("u1", "A", ts="2026-01-01T00:00:00")
    mem.add("u1", "B", ts="2026-01-02T00:00:00")
    block = mem.context_block("u1")
    # 依時間由舊到新呈現
    assert block.index("A") < block.index("B")
