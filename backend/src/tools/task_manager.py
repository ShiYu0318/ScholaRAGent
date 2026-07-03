"""簡單的本地任務排程器：協助使用者記錄與組織待辦，持久化為 JSON。

外部行事曆 / Google Docs 整合需憑證，這裡先提供不需外部服務的本地實作，
之後可再接上真正的 Calendar/Docs API。
"""
import json
import os
from datetime import datetime, timezone

from src import config
from src.utils.logger import get_logger


class TaskManager:
    def __init__(self, path=None):
        self.logger = get_logger(self.__class__.__name__)
        self.path = str(path or config.TASKS_PATH)
        self._tasks = []
        self.load()

    def add_task(self, title, due=None):
        """新增待辦，回傳確認字串（供工具呼叫直接回覆）。"""
        task = {
            "id": len(self._tasks) + 1,
            "title": title,
            "due": due or "",
            "done": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._tasks.append(task)
        self.save()
        due_str = f"（截止：{due}）" if due else ""
        return f"已新增待辦 #{task['id']}：{title}{due_str}"

    def list_tasks(self, include_done=False):
        items = self._tasks if include_done else [t for t in self._tasks if not t["done"]]
        if not items:
            return "目前沒有待辦事項。"
        return "\n".join(
            f"#{t['id']} {'' if t['done'] else ''} {t['title']}"
            + (f"（截止 {t['due']}）" if t["due"] else "")
            for t in items
        )

    def complete_task(self, task_id):
        for t in self._tasks:
            if t["id"] == int(task_id):
                t["done"] = True
                self.save()
                return f"已完成待辦 #{task_id}：{t['title']}"
        return f"找不到待辦 #{task_id}"

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"任務存檔失敗：{e}")

    def load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, encoding="utf-8") as f:
                    self._tasks = json.load(f)
        except Exception as e:
            self.logger.error(f"任務載入失敗：{e}")
            self._tasks = []
