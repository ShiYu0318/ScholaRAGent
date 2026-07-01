"""長期記憶模組：管理、動態過濾與壓縮（Week7）。

每則記憶是 {user_id, kind, content, ts}。提供依種類/關鍵字/近期的動態過濾，
以及當某使用者記憶過多時，用注入的 summarizer 把較舊記憶壓縮成一則摘要，
保留最近數則原文，控制 context 長度。持久化為 JSON。
"""
import json
import os
from datetime import datetime, timezone

from src import config
from src.utils.logger import get_logger


def _now():
    return datetime.now(timezone.utc).isoformat()


class MemoryStore:
    def __init__(self, path=None, max_items=50, keep_recent=10):
        self.logger = get_logger(self.__class__.__name__)
        self.path = path or config.MEMORY_PATH
        self.max_items = max_items          # 單一使用者觸發壓縮的門檻
        self.keep_recent = keep_recent      # 壓縮時保留的最近原文則數
        self._mem = {}                      # {user_id: [記憶, ...]}
        self.load()

    def add(self, user_id, content, kind="note", ts=None):
        item = {"kind": kind, "content": content, "ts": ts or _now()}
        self._mem.setdefault(str(user_id), []).append(item)
        self.save()
        return item

    def all(self, user_id):
        return list(self._mem.get(str(user_id), []))

    def filter(self, user_id, kind=None, contains=None, limit=None):
        """動態過濾：可依 kind、內容關鍵字，取最近 limit 則。"""
        items = self._mem.get(str(user_id), [])
        if kind is not None:
            items = [m for m in items if m["kind"] == kind]
        if contains:
            needle = contains.lower()
            items = [m for m in items if needle in m["content"].lower()]
        # 依時間排序（新到舊）
        items = sorted(items, key=lambda m: m["ts"], reverse=True)
        if limit is not None:
            items = items[:limit]
        return items

    def compress(self, user_id, summarizer):
        """記憶超量時，把較舊記憶壓縮成單一摘要，保留最近 keep_recent 則。

        summarizer：callable(list[str]) -> str，通常包裝 LLM。
        回傳是否有執行壓縮。
        """
        uid = str(user_id)
        items = self._mem.get(uid, [])
        if len(items) <= self.max_items:
            return False

        items = sorted(items, key=lambda m: m["ts"])
        cut = len(items) - self.keep_recent
        old, recent = items[:cut], items[cut:]
        # 已經是壓縮摘要的不重複塞入，只取內容
        summary_text = summarizer([m["content"] for m in old])
        compressed = {"kind": "summary", "content": summary_text, "ts": _now()}
        self._mem[uid] = [compressed] + recent
        self.save()
        self.logger.info(f"使用者 {uid} 記憶壓縮：{len(old)} 則 → 1 則摘要")
        return True

    def context_block(self, user_id, limit=10):
        """組出可直接餵給 LLM 的記憶區塊字串。"""
        items = self.filter(user_id, limit=limit)
        if not items:
            return ""
        return "\n".join(f"- ({m['kind']}) {m['content']}" for m in reversed(items))

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._mem, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"記憶存檔失敗：{e}")

    def load(self):
        try:
            if self.path and os.path.exists(self.path):
                with open(self.path, encoding="utf-8") as f:
                    self._mem = json.load(f)
        except Exception as e:
            self.logger.error(f"記憶載入失敗，改用空記憶：{e}")
            self._mem = {}
