"""Telegram 推送：透過 Bot API sendMessage。需 TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID。"""
import requests

from src.notify.base import Notifier


class TelegramNotifier(Notifier):
    name = "telegram"

    def __init__(self, token=None, chat_id=None, session=None):
        super().__init__()
        self.token = token
        self.chat_id = chat_id
        self.session = session or requests

    @property
    def enabled(self):
        return bool(self.token and self.chat_id)

    def send(self, text, timeout=10):
        if not self.enabled:
            self.logger.info("Telegram 未設定，略過")
            return False
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": text, "disable_web_page_preview": True}
        try:
            resp = self.session.post(url, json=payload, timeout=timeout)
            ok = getattr(resp, "status_code", 200) == 200
            if not ok:
                self.logger.error(f"Telegram 發送失敗：HTTP {resp.status_code}")
            return ok
        except Exception as e:
            self.logger.error(f"Telegram 發送例外：{e}")
            return False
