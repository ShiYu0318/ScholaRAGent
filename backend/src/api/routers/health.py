"""健康監控端點。

未登入只回存活狀態（給負載平衡器 / 監控探針用）；儲存統計、排程器狀態、
外部服務是否已設定等細節只給已登入使用者，避免對外暴露系統組態。
"""
from fastapi import APIRouter, Depends

from src import config
from src.api.deps import get_optional_user, get_store
from src.store.base import Store

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health(user=Depends(get_optional_user), store: Store = Depends(get_store)):
    if user is None:
        return {"status": "ok", "version": "2.0.0"}
    from src.scheduler import get_scheduler_manager
    providers = {
        "groq": bool(config.GROQ_API_KEY),
        "telegram": bool(config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID),
        "email": bool(config.SMTP_HOST and config.SMTP_FROM),
        "line": bool(config.LINE_CHANNEL_TOKEN),
        "discord_bot": bool(config.DISCORD_BOT_TOKEN),
        "google_oauth": bool(config.GOOGLE_CLIENT_ID and config.GOOGLE_CLIENT_SECRET),
        "github_oauth": bool(config.GITHUB_CLIENT_ID and config.GITHUB_CLIENT_SECRET),
        "discord_oauth": bool(config.DISCORD_CLIENT_ID and config.DISCORD_CLIENT_SECRET),
    }
    return {
        "status": "ok",
        "version": "2.0.0",
        "store_backend": config.STORE_BACKEND,
        "store": store.stats(),
        "scheduler": get_scheduler_manager().status(),
        "providers": providers,
    }
