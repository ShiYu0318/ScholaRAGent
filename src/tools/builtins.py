"""內建工具集：把向量庫、趨勢分析、任務排程包裝成可被 LLM 呼叫的工具。"""
from src.analysis import trends
from src.tools.registry import ToolRegistry
from src.tools.task_manager import TaskManager


def build_default_registry(store=None, task_manager=None):
    """建立內建工具註冊表。store 提供論文檢索，task_manager 提供待辦排程。"""
    registry = ToolRegistry()
    tasks = task_manager or TaskManager()

    def search_papers(query, k=3):
        if store is None:
            return "（未連接知識庫）"
        results = store.search(query, k=int(k))
        if not results:
            return "知識庫中找不到相關論文。"
        return "\n".join(f"- {p['title']}（{p.get('link', '')}）" for p in results)

    def list_trending(top_n=5):
        if store is None or not getattr(store, "papers", None):
            return "目前資料不足以分析趨勢。"
        rising = trends.trending_keywords(store.papers, top_n=int(top_n))
        if not rising:
            return "目前沒有明顯上升的關鍵字。"
        return "、".join(f"{kw}" for kw, _ in rising)

    registry.register(
        "search_papers",
        "在已收錄的 AI 論文知識庫中檢索與 query 最相關的論文標題與連結。",
        {"properties": {
            "query": {"type": "string", "description": "檢索關鍵字或問題"},
            "k": {"type": "integer", "description": "回傳幾篇，預設 3"},
        }, "required": ["query"]},
        search_papers,
    )
    registry.register(
        "list_trending",
        "列出目前 AI 論文中正在上升的熱門關鍵字。",
        {"properties": {"top_n": {"type": "integer", "description": "回傳幾個關鍵字"}},
         "required": []},
        list_trending,
    )
    registry.register(
        "add_task",
        "替使用者新增一則待辦事項（可含截止日）。",
        {"properties": {
            "title": {"type": "string", "description": "待辦內容"},
            "due": {"type": "string", "description": "截止日期，如 2026-07-10，可省略"},
        }, "required": ["title"]},
        lambda title, due=None: tasks.add_task(title, due),
    )
    registry.register(
        "list_tasks",
        "列出目前所有未完成的待辦事項。",
        {"properties": {}, "required": []},
        lambda: tasks.list_tasks(),
    )
    return registry
