"""build_bot 整合煙霧測試：確認所有斜線指令都註冊、且建構過程無誤。

以 fake 取代會下載模型 / 連網的 VectorStore、GroqClient，DB/記憶導向 tmp。
"""
from src.bot import discord_bot
from src import config


class FakeStore:
    def __init__(self, *a, **k):
        self.papers = []

    def add(self, papers):
        self.papers.extend(papers)
        return papers

    def search(self, *a, **k):
        return []


def test_build_bot_registers_all_commands(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(config, "MEMORY_PATH", tmp_path / "m.json")
    monkeypatch.setattr(discord_bot, "VectorStore", lambda *a, **k: FakeStore())
    monkeypatch.setattr(discord_bot, "GroqClient", lambda *a, **k: object())

    bot = discord_bot.build_bot()
    names = {c.name for c in bot.tree.get_commands()}
    expected = {"daily", "ask", "report", "compare", "trends", "sources",
                "latex", "slides", "review", "like", "agent", "set_push_time", "help"}
    assert expected <= names
