"""RAGency 統一進入點（在 backend/ 目錄下執行）：

    uv run python main.py api    # 儀表板 API :8000（frontend/dist 存在時一併服務前端）
    uv run python main.py bot    # Discord bot
    uv run python main.py all    # 同時啟動 API 與 bot

開發前端時另開一個終端機：cd ../frontend && npm run dev（:5173，proxy /api → :8000）。
"""
import argparse
import threading

from src import config
from src.utils.logger import get_logger

logger = get_logger("Main")


def run_api(host="0.0.0.0", port=8000):
    import uvicorn
    logger.info(f"啟動儀表板 API：http://localhost:{port}（Swagger：/docs）")
    uvicorn.run("src.api.app:app", host=host, port=port)


def run_bot():
    if not config.DISCORD_BOT_TOKEN:
        logger.error("缺少 DISCORD_BOT_TOKEN，請在 backend/.env 設定")
        return
    if not config.GROQ_API_KEY:
        logger.error("缺少 GROQ_API_KEY，請在 backend/.env 設定")
        return
    from src.bot.discord_bot import build_bot
    bot = build_bot()
    logger.info("啟動 RAGency Discord bot…")
    bot.run(config.DISCORD_BOT_TOKEN)


def main():
    parser = argparse.ArgumentParser(description="RAGency 進入點")
    parser.add_argument("mode", nargs="?", default="api",
                        choices=["api", "bot", "all"],
                        help="api（預設）｜bot｜all")
    parser.add_argument("--port", type=int, default=8000, help="API 埠號")
    args = parser.parse_args()

    if args.mode == "api":
        run_api(port=args.port)
    elif args.mode == "bot":
        run_bot()
    else:
        # bot 的 event loop 需要主執行緒，API 放到背景執行緒
        api_thread = threading.Thread(
            target=run_api, kwargs={"port": args.port}, daemon=True)
        api_thread.start()
        run_bot()


if __name__ == "__main__":
    main()
