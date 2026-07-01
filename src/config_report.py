"""設定韌性檢查（E4）：集中回報缺哪些必填、哪些選配功能已啟用。

啟動時可據此清楚提示使用者「哪些功能因缺金鑰而降級」，而非默默失敗。
"""
_REQUIRED = ["GROQ_API_KEY", "DISCORD_BOT_TOKEN", "DISCORD_CHANNEL_ID"]


def config_report(cfg):
    """回傳 {ok, missing_required, features}。cfg 為具對應屬性的物件。"""
    missing = [k for k in _REQUIRED if not getattr(cfg, k, None)]
    features = {
        "telegram": bool(getattr(cfg, "TELEGRAM_BOT_TOKEN", "")),
        "email": bool(getattr(cfg, "SMTP_HOST", "")),
        "line": bool(getattr(cfg, "LINE_CHANNEL_TOKEN", "")),
        "twitter": bool(getattr(cfg, "X_BEARER_TOKEN", "")),
        "reranker": bool(getattr(cfg, "RERANK_ENABLED", False)),
    }
    return {"ok": not missing, "missing_required": missing, "features": features}
