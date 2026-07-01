"""LINE 推送：透過 Messaging API push endpoint。

需 LINE_CHANNEL_TOKEN（Channel access token）與 LINE_TO（user/group id）。
註：LINE Notify 已於 2025 年停止服務，故改用 Messaging API。
"""
import requests

from src.notify.base import Notifier

_PUSH = "https://api.line.me/v2/bot/message/push"


class LineNotifier(Notifier):
    name = "line"

    def __init__(self, channel_token=None, to=None, session=None):
        super().__init__()
        self.channel_token = channel_token
        self.to = to
        self.session = session or requests

    @property
    def enabled(self):
        return bool(self.channel_token and self.to)

    def send(self, text, timeout=10):
        if not self.enabled:
            self.logger.info("LINE 未設定，略過")
            return False
        headers = {
            "Authorization": f"Bearer {self.channel_token}",
            "Content-Type": "application/json",
        }
        # LINE 單則文字上限 5000 字元
        payload = {"to": self.to, "messages": [{"type": "text", "text": text[:5000]}]}
        try:
            resp = self.session.post(_PUSH, headers=headers, json=payload, timeout=timeout)
            ok = getattr(resp, "status_code", 200) == 200
            if not ok:
                self.logger.error(f"LINE 發送失敗：HTTP {resp.status_code}")
            return ok
        except Exception as e:
            self.logger.error(f"LINE 發送例外：{e}")
            return False
