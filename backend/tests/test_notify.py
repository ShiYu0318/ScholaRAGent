"""多平台推送：enabled 判定、payload 組裝、dispatcher 廣播（全用注入，無網路）。"""
from types import SimpleNamespace

from src.notify.telegram import TelegramNotifier
from src.notify.email_notifier import EmailNotifier
from src.notify.line import LineNotifier
from src.notify import dispatcher


class FakeResp:
    def __init__(self, status=200):
        self.status_code = status


class FakeSession:
    def __init__(self, status=200):
        self.calls = []
        self.status = status

    def post(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return FakeResp(self.status)


# ---- Telegram ----
def test_telegram_disabled_without_creds():
    assert TelegramNotifier().enabled is False
    assert TelegramNotifier(token="t", chat_id="c").enabled is True


def test_telegram_send_builds_payload():
    sess = FakeSession()
    n = TelegramNotifier(token="TOK", chat_id="123", session=sess)
    assert n.send("hello") is True
    call = sess.calls[0]
    assert "botTOK/sendMessage" in call["url"]
    assert call["json"]["chat_id"] == "123"
    assert call["json"]["text"] == "hello"


def test_telegram_send_skipped_when_disabled():
    sess = FakeSession()
    assert TelegramNotifier(session=sess).send("x") is False
    assert sess.calls == []


# ---- LINE ----
def test_line_payload_and_truncation():
    sess = FakeSession()
    n = LineNotifier(channel_token="CT", to="U1", session=sess)
    assert n.send("a" * 6000) is True
    msg = sess.calls[0]["json"]["messages"][0]
    assert msg["type"] == "text"
    assert len(msg["text"]) == 5000  # 截斷到 5000
    assert sess.calls[0]["headers"]["Authorization"] == "Bearer CT"


# ---- Email ----
class FakeSMTP:
    instances = []

    def __init__(self, host, port, timeout=10):
        self.host = host
        self.sent = []
        self.tls = False
        FakeSMTP.instances.append(self)

    def starttls(self):
        self.tls = True

    def login(self, u, p):
        self.creds = (u, p)

    def sendmail(self, sender, to, body):
        self.sent.append((sender, to, body))

    def quit(self):
        self.quit_called = True


def test_email_disabled_without_recipients():
    assert EmailNotifier(host="h", sender="a@b.com").enabled is False
    assert EmailNotifier(host="h", sender="a@b.com", recipients=["c@d.com"]).enabled is True


def test_email_send_uses_smtp():
    FakeSMTP.instances.clear()
    n = EmailNotifier(host="smtp.test", port=587, user="u", password="p",
                      sender="from@test.com", recipients=["to@test.com"],
                      smtp_factory=FakeSMTP)
    assert n.send("每日摘要") is True
    smtp = FakeSMTP.instances[0]
    assert smtp.tls is True
    assert smtp.sent[0][0] == "from@test.com"
    assert "to@test.com" in smtp.sent[0][1]
    assert smtp.quit_called is True


def test_email_build_message_headers():
    n = EmailNotifier(host="h", sender="from@test.com", recipients=["a@x.com", "b@x.com"])
    msg = n.build_message("body", subject="主旨")
    assert msg["From"] == "from@test.com"
    assert "a@x.com" in msg["To"] and "b@x.com" in msg["To"]
    assert msg["Subject"] == "主旨"


# ---- Dispatcher ----
def _cfg(**over):
    base = dict(
        TELEGRAM_BOT_TOKEN="", TELEGRAM_CHAT_ID="",
        SMTP_HOST="", SMTP_PORT=587, SMTP_USER="", SMTP_PASSWORD="",
        SMTP_FROM="", EMAIL_TO="",
        LINE_CHANNEL_TOKEN="", LINE_TO="",
    )
    base.update(over)
    return SimpleNamespace(**base)


def test_dispatcher_none_enabled_by_default():
    assert dispatcher.enabled_notifiers(_cfg()) == []


def test_dispatcher_enables_configured_platforms():
    cfg = _cfg(TELEGRAM_BOT_TOKEN="t", TELEGRAM_CHAT_ID="c",
               EMAIL_TO="a@x.com", SMTP_HOST="h", SMTP_FROM="f@x.com")
    names = {n.name for n in dispatcher.enabled_notifiers(cfg)}
    assert names == {"telegram", "email"}


def test_broadcast_collects_results():
    class Dummy:
        def __init__(self, name, ok):
            self.name = name
            self._ok = ok

        def send(self, text):
            return self._ok

    results = dispatcher.broadcast("hi", notifiers=[Dummy("a", True), Dummy("b", False)])
    assert results == {"a": True, "b": False}
