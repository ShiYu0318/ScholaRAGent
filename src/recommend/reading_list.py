"""閱讀看板（Recommend / D7）：追蹤自己的研究線。

論文分 to-read / reading / done 三欄，可加標籤與筆記，JSON 持久化。
解決研究生「讀了一堆卻散落各處、追不回自己的閱讀進度」的痛點。
"""
import json

from src.utils.logger import get_logger

STATES = ("to-read", "reading", "done")


class ReadingList:
    def __init__(self, path):
        self.logger = get_logger(self.__class__.__name__)
        self.path = path
        self._items = {}       # id -> {id, title, state, tags, note}
        self._load()

    def add(self, paper_id, title, state="to-read", tags=None, note=""):
        if state not in STATES:
            raise ValueError(f"未知狀態：{state}（可用 {STATES}）")
        self._items[paper_id] = {
            "id": paper_id, "title": title, "state": state,
            "tags": list(tags or []), "note": note,
        }
        self._save()

    def set_state(self, paper_id, state):
        if state not in STATES:
            raise ValueError(f"未知狀態：{state}")
        if paper_id in self._items:
            self._items[paper_id]["state"] = state
            self._save()

    def items(self, state=None):
        vals = list(self._items.values())
        return [i for i in vals if i["state"] == state] if state else vals

    def _save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(list(self._items.values()), f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"儲存閱讀看板失敗：{e}")

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                for it in json.load(f):
                    self._items[it["id"]] = it
        except FileNotFoundError:
            pass
        except Exception as e:
            self.logger.error(f"載入閱讀看板失敗：{e}")
