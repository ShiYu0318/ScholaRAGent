"""工具呼叫框架：registry、task_manager、builtins、tool_agent 迴圈。"""
from types import SimpleNamespace

import pytest

from src.tools.registry import ToolRegistry
from src.tools.task_manager import TaskManager
from src.tools import builtins
from src.agent.tool_agent import ToolAgent
from src import config
from tests.conftest import make_paper


# ---- registry ----
def test_register_and_spec():
    reg = ToolRegistry()
    reg.register("echo", "回聲", {"properties": {"x": {"type": "string"}}, "required": ["x"]},
                 lambda x: f"got {x}")
    spec = reg.specs()[0]
    assert spec["type"] == "function"
    assert spec["function"]["name"] == "echo"
    assert spec["function"]["parameters"]["required"] == ["x"]


def test_execute_with_dict_and_json():
    reg = ToolRegistry()
    reg.register("add", "加", {"properties": {}, "required": []}, lambda a, b: a + b)
    assert reg.execute("add", {"a": 2, "b": 3}) == "5"
    assert reg.execute("add", '{"a": 4, "b": 6}') == "10"


def test_execute_unknown_and_error():
    reg = ToolRegistry()
    reg.register("boom", "炸", {"properties": {}, "required": []},
                 lambda: (_ for _ in ()).throw(ValueError("x")))
    assert "未知工具" in reg.execute("nope", {})
    assert "執行錯誤" in reg.execute("boom", {})


# ---- task manager ----
def test_task_manager_add_list_complete(tmp_path):
    tm = TaskManager(path=tmp_path / "tasks.json")
    assert "已新增待辦 #1" in tm.add_task("寫報告", due="2026-07-10")
    tm.add_task("讀論文")
    listing = tm.list_tasks()
    assert "寫報告" in listing and "讀論文" in listing
    tm.complete_task(1)
    assert "寫報告" not in tm.list_tasks()          # 完成後不在未完成清單
    assert "寫報告" in tm.list_tasks(include_done=True)


def test_task_manager_persistence(tmp_path):
    p = tmp_path / "tasks.json"
    TaskManager(path=p).add_task("持久化")
    assert "持久化" in TaskManager(path=p).list_tasks()


# ---- builtins ----
class FakeStore:
    def __init__(self, papers):
        self.papers = papers

    def search(self, query, k=3):
        return self.papers[:k]


def test_builtins_search_and_tasks(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TASKS_PATH", tmp_path / "tasks.json")
    store = FakeStore([make_paper("1", "Agent Paper"), make_paper("2", "RAG Paper")])
    reg = builtins.build_default_registry(store=store)
    assert set(reg.names()) == {"search_papers", "list_trending", "add_task",
                                "list_tasks", "add_calendar_event"}
    assert "Agent Paper" in reg.execute("search_papers", {"query": "agent", "k": 1})
    assert "已新增待辦" in reg.execute("add_task", {"title": "demo"})
    assert "demo" in reg.execute("list_tasks", {})


# ---- tool agent loop ----
def _msg(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def _resp(message):
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class ScriptedCompletions:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


class ScriptedClient:
    def __init__(self, responses):
        self.chat = SimpleNamespace(completions=ScriptedCompletions(responses))


def test_tool_agent_executes_tool_then_answers():
    reg = ToolRegistry()
    reg.register("greet", "打招呼", {"properties": {"name": {"type": "string"}}, "required": ["name"]},
                 lambda name: f"hi {name}")
    tool_call = SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(name="greet", arguments='{"name": "Ada"}'),
    )
    responses = [
        _resp(_msg(content=None, tool_calls=[tool_call])),   # 第一步：要求呼叫工具
        _resp(_msg(content="已完成問候。", tool_calls=None)),  # 第二步：最終回覆
    ]
    client = ScriptedClient(responses)
    agent = ToolAgent(client, reg, model="test")
    out = agent.run("跟 Ada 打招呼")
    assert out == "已完成問候。"
    # 第二次呼叫的 messages 內應含 tool 執行結果
    second_call_messages = client.chat.completions.calls[1]["messages"]
    assert any(m.get("role") == "tool" and "hi Ada" in m["content"] for m in second_call_messages)


def test_tool_agent_direct_answer_without_tools():
    reg = ToolRegistry()
    client = ScriptedClient([_resp(_msg(content="直接回答", tool_calls=None))])
    agent = ToolAgent(client, reg, model="test")
    assert agent.run("你好") == "直接回答"
