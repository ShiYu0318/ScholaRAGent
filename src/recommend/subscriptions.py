"""訂閱式主題快報。

使用者訂閱關鍵字（或作者），新論文進來時比對命中的訂閱，只推相關的。
把「每日 firehose」升級成「我關心的主題有新進展才通知」。JSON 持久化。
"""
import json

from src.utils.logger import get_logger


class Subscriptions:
    def __init__(self, path):
        self.logger = get_logger(self.__class__.__name__)
        self.path = path
        self._subs = {}       # name -> {name, keywords}
        self._load()

    def add(self, name, keywords):
        self._subs[name] = {"name": name, "keywords": [k.lower() for k in keywords]}
        self._save()

    def remove(self, name):
        if self._subs.pop(name, None) is not None:
            self._save()

    def all(self):
        return list(self._subs.values())

    def matches(self, paper):
        """回傳此論文命中的訂閱名稱清單。"""
        text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
        return [s["name"] for s in self._subs.values()
                if any(kw in text for kw in s["keywords"])]

    def _save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(list(self._subs.values()), f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"儲存訂閱失敗：{e}")

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                for s in json.load(f):
                    self._subs[s["name"]] = s
        except FileNotFoundError:
            pass
        except Exception as e:
            self.logger.error(f"載入訂閱失敗：{e}")
