"""Email 推送：透過 SMTP 寄信。需 SMTP_HOST / SMTP_FROM / EMAIL_TO（帳密視伺服器而定）。

smtp_factory 可注入以便測試（預設用 smtplib.SMTP）。
"""
import smtplib
from email.mime.text import MIMEText

from src.notify.base import Notifier


def _default_smtp(host, port, timeout=10):
    return smtplib.SMTP(host, port, timeout=timeout)


class EmailNotifier(Notifier):
    name = "email"

    def __init__(self, host=None, port=587, user=None, password=None,
                 sender=None, recipients=None, use_tls=True, smtp_factory=None):
        super().__init__()
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.sender = sender or user
        self.recipients = recipients or []
        self.use_tls = use_tls
        self.smtp_factory = smtp_factory or _default_smtp

    @property
    def enabled(self):
        return bool(self.host and self.sender and self.recipients)

    def build_message(self, text, subject="AIR Agent 每日 AI 摘要"):
        msg = MIMEText(text, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = ", ".join(self.recipients)
        return msg

    def send(self, text, subject="AIR Agent 每日 AI 摘要"):
        if not self.enabled:
            self.logger.info("Email 未設定，略過")
            return False
        msg = self.build_message(text, subject)
        try:
            server = self.smtp_factory(self.host, self.port)
            try:
                if self.use_tls:
                    server.starttls()
                if self.user and self.password:
                    server.login(self.user, self.password)
                server.sendmail(self.sender, self.recipients, msg.as_string())
            finally:
                server.quit()
            return True
        except Exception as e:
            self.logger.error(f"Email 發送失敗：{e}")
            return False
