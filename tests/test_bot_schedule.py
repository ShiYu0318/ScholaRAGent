"""discord_bot 排程持久化與訊息分段的純邏輯測試。"""
from src.bot import discord_bot
from src import config


def test_split_short_text():
    assert discord_bot._split("hello") == ["hello"]


def test_split_empty_returns_one_empty():
    assert discord_bot._split("") == [""]


def test_split_long_text_chunks():
    text = "x" * 4200
    chunks = discord_bot._split(text, size=1900)
    assert len(chunks) == 3
    assert all(len(c) <= 1900 for c in chunks)
    assert "".join(chunks) == text


def test_schedule_save_and_load(isolated_data):
    discord_bot._save_schedule(9, 30)
    assert config.SCHEDULE_PATH.exists()
    assert discord_bot._load_schedule() == (9, 30)


def test_schedule_load_default_when_missing(isolated_data):
    # 檔案不存在時回退到 config 預設值
    assert not config.SCHEDULE_PATH.exists()
    assert discord_bot._load_schedule() == (config.PUSH_HOUR, config.PUSH_MINUTE)
