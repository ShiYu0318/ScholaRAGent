"""閱讀看板，JSON 持久化。"""
import pytest

from src.recommend.reading_list import ReadingList


def test_add_and_filter_by_state(tmp_path):
    rl = ReadingList(tmp_path / "r.json")
    rl.add("1", "Paper A")
    rl.add("2", "Paper B", state="reading")
    assert {i["id"] for i in rl.items("to-read")} == {"1"}
    assert {i["id"] for i in rl.items("reading")} == {"2"}
    assert len(rl.items()) == 2


def test_set_state_moves_between_columns(tmp_path):
    rl = ReadingList(tmp_path / "r.json")
    rl.add("1", "Paper A")
    rl.set_state("1", "done")
    assert rl.items("to-read") == []
    assert rl.items("done")[0]["id"] == "1"


def test_persists_across_instances(tmp_path):
    path = tmp_path / "r.json"
    rl = ReadingList(path)
    rl.add("1", "Paper A", tags=["rag"])
    reloaded = ReadingList(path)
    item = reloaded.items("to-read")[0]
    assert item["title"] == "Paper A"
    assert item["tags"] == ["rag"]


def test_invalid_state_rejected(tmp_path):
    rl = ReadingList(tmp_path / "r.json")
    with pytest.raises(ValueError):
        rl.add("1", "A", state="bogus")


def test_add_is_idempotent_on_id(tmp_path):
    rl = ReadingList(tmp_path / "r.json")
    rl.add("1", "A")
    rl.add("1", "A again", state="reading")   # 同 id 更新而非重複
    assert len(rl.items()) == 1
    assert rl.items("reading")[0]["title"] == "A again"
