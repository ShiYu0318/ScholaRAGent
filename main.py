"""AIR Agent 進入點：啟動 Discord bot。"""
from src import config
from src.bot.discord_bot import build_bot
from src.utils.logger import get_logger

logger = get_logger("Main")


def main():
    if not config.DISCORD_BOT_TOKEN:
        logger.error("缺少 DISCORD_BOT_TOKEN，請在 .env 設定")
        return
    if not config.GROQ_API_KEY:
        logger.error("缺少 GROQ_API_KEY，請在 .env 設定")
        return

    bot = build_bot()
    logger.info("啟動 AIR Agent Discord bot…")
    bot.run(config.DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    main()
