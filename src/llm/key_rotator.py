"""多金鑰輪替（LLM / E7，受 meetGRAG 啟發）。

大量呼叫（如建索引、批次摘要）容易撞免費方案的速率上限。KeyRotator 以
round-robin 分散負載，遇到某把 key 被限流時把它冷卻一段時間、暫時跳過，
冷卻結束再納回輪替。時鐘可注入，離線可測。
"""
import time

from src.utils.logger import get_logger


class KeyRotator:
    def __init__(self, keys, cooldown=60, now=time.monotonic):
        if not keys:
            raise ValueError("KeyRotator 需要至少一把金鑰")
        self.logger = get_logger(self.__class__.__name__)
        self.keys = list(keys)
        self.cooldown = cooldown
        self._now = now
        self._i = 0
        self._blocked = {}       # key -> 解除冷卻的時間點

    def next(self):
        """回傳下一把可用金鑰；全被冷卻時回傳最快恢復的那把。"""
        n = len(self.keys)
        for _ in range(n):
            key = self.keys[self._i % n]
            self._i += 1
            if self._blocked.get(key, 0) <= self._now():
                return key
        # 全部冷卻中：挑最早會恢復的
        return min(self.keys, key=lambda k: self._blocked.get(k, 0))

    def mark_rate_limited(self, key):
        """標記某把金鑰被限流，冷卻 cooldown 秒。"""
        self._blocked[key] = self._now() + self.cooldown
        self.logger.info(f"金鑰 …{str(key)[-4:]} 被限流，冷卻 {self.cooldown}s")
