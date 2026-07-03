"""推送分派器：依設定建立各平台 notifier，統一廣播訊息。"""
from src import config
from src.notify.email_notifier import EmailNotifier
from src.notify.line import LineNotifier
from src.notify.telegram import TelegramNotifier
from src.utils.logger import get_logger

logger = get_logger("NotifyDispatcher")


def build_notifiers(cfg=config):
    """依設定建立所有 notifier（含未啟用者）。"""
    return [
        TelegramNotifier(
            token=getattr(cfg, "TELEGRAM_BOT_TOKEN", ""),
            chat_id=getattr(cfg, "TELEGRAM_CHAT_ID", ""),
        ),
        EmailNotifier(
            host=getattr(cfg, "SMTP_HOST", ""),
            port=getattr(cfg, "SMTP_PORT", 587),
            user=getattr(cfg, "SMTP_USER", ""),
            password=getattr(cfg, "SMTP_PASSWORD", ""),
            sender=getattr(cfg, "SMTP_FROM", ""),
            recipients=[r for r in getattr(cfg, "EMAIL_TO", "").split(",") if r.strip()],
        ),
        LineNotifier(
            channel_token=getattr(cfg, "LINE_CHANNEL_TOKEN", ""),
            to=getattr(cfg, "LINE_TO", ""),
        ),
    ]


def enabled_notifiers(cfg=config):
    return [n for n in build_notifiers(cfg) if n.enabled]


def broadcast(text, cfg=config, notifiers=None):
    """把 text 送到所有已啟用的平台，回傳 {平台名: 是否成功}。"""
    notifiers = notifiers if notifiers is not None else enabled_notifiers(cfg)
    results = {}
    for n in notifiers:
        results[n.name] = n.send(text)
    if not results:
        logger.info("目前沒有啟用任何額外推送平台（僅 Discord）")
    return results
