"""Discord bot：每日排程推送論文摘要、RAG 問答、主題研究報告。"""
import asyncio
import json
from datetime import time, timedelta, timezone

import discord
from discord.ext import commands, tasks

from src import config
from src.crawlers.arxiv_crawler import ArxivCrawler
from src.llm.groq_client import GroqClient
from src.rag.vector_store import VectorStore
from src.utils.file_manager import save_to_text
from src.utils.logger import get_logger

logger = get_logger("DiscordBot")

_TZ = timezone(timedelta(hours=config.PUSH_TZ_OFFSET))


def _load_schedule():
    """讀取使用者設定的推送時間（hour, minute），未設定則用 config 預設值。"""
    if config.SCHEDULE_PATH.exists():
        try:
            data = json.loads(config.SCHEDULE_PATH.read_text(encoding="utf-8"))
            return int(data["hour"]), int(data["minute"])
        except Exception as e:
            logger.error(f"讀取推送時間設定失敗，改用預設值：{e}")
    return config.PUSH_HOUR, config.PUSH_MINUTE


def _save_schedule(hour, minute):
    config.SCHEDULE_PATH.write_text(
        json.dumps({"hour": hour, "minute": minute}), encoding="utf-8"
    )


def _push_time():
    """組出帶時區的 datetime.time，供 tasks.loop 排程。"""
    hour, minute = _load_schedule()
    return time(hour=hour, minute=minute, tzinfo=_TZ)


def build_bot():
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

    crawler = ArxivCrawler(query=config.ARXIV_QUERY)
    llm = GroqClient()
    store = VectorStore()

    async def collect_and_summarize(limit):
        """背景執行緒跑爬蟲＋摘要＋寫入向量庫，回傳含摘要的論文清單。"""
        def _work():
            papers = crawler.fetch_latest_papers(limit=limit)
            for p in papers:
                p["summary"] = llm.summarize(p)
            if papers:
                store.add(papers)
                save_to_text(papers, source_name="arxiv")
            return papers

        return await asyncio.to_thread(_work)

    def paper_embed(paper):
        embed = discord.Embed(
            title=paper["title"][:256],
            url=paper["link"],
            description=paper.get("summary", paper["abstract"])[:1024],
            color=0x4F46E5,
        )
        embed.add_field(name="作者", value=paper["authors"][:200] or "—", inline=False)
        embed.set_footer(text=f"arXiv {paper['id']} · {paper['published']}")
        return embed

    async def push_daily(channel):
        await channel.send(f"📰 **今日 AI 論文推送**（{config.ARXIV_QUERY}）")
        papers = await collect_and_summarize(config.DAILY_COUNT)
        if not papers:
            await channel.send("⚠️ 今天沒有抓到論文。")
            return
        for p in papers:
            await channel.send(embed=paper_embed(p))
        await channel.send("✅ 推送完成，可用 `/ask <問題>` 針對論文發問。")

    async def build_report(topic):
        """背景搜尋主題相關論文、寫入向量庫，並產生研究報告。"""
        def _work():
            papers = crawler.search_topic(topic, limit=config.REPORT_COUNT)
            if papers:
                store.add(papers)
                save_to_text(papers, source_name="arxiv")
            report = llm.research_report(topic, papers)
            return report, papers

        return await asyncio.to_thread(_work)

    @tasks.loop(time=_push_time())
    async def daily_task():
        channel = bot.get_channel(config.DISCORD_CHANNEL_ID)
        if channel is None:
            logger.error(f"找不到頻道 {config.DISCORD_CHANNEL_ID}，跳過排程推送")
            return
        logger.info("執行每日排程推送")
        await push_daily(channel)

    @bot.event
    async def on_ready():
        logger.info(f"已登入為 {bot.user}")
        try:
            if config.DISCORD_GUILD_ID:
                guild = discord.Object(id=config.DISCORD_GUILD_ID)
                bot.tree.copy_global_to(guild=guild)
                synced = await bot.tree.sync(guild=guild)
                logger.info(f"已同步 {len(synced)} 個斜線指令到伺服器 {config.DISCORD_GUILD_ID}")
            else:
                synced = await bot.tree.sync()
                logger.info(f"已全域同步 {len(synced)} 個斜線指令（最久 1 小時生效）")
        except Exception as e:
            logger.error(f"同步斜線指令失敗：{e}")
        if not daily_task.is_running():
            daily_task.start()

    @bot.tree.command(name="daily", description="立即抓取並推送今日 AI 論文")
    async def daily_cmd(interaction: discord.Interaction):
        await interaction.response.send_message("⏳ 開始抓取今日論文…", ephemeral=True)
        await push_daily(interaction.channel)

    @bot.tree.command(name="ask", description="依據已收錄論文回答你的問題")
    @discord.app_commands.describe(question="你想詢問的問題")
    async def ask_cmd(interaction: discord.Interaction, question: str):
        if not question.strip():
            await interaction.response.send_message("用法：`/ask 你的問題`", ephemeral=True)
            return
        await interaction.response.defer(thinking=True)
        papers = store.search(question, k=4)
        answer = await asyncio.to_thread(llm.answer, question, papers)
        chunks = _split(answer)
        await interaction.followup.send(chunks[0])
        for chunk in chunks[1:]:
            await interaction.channel.send(chunk)

    @bot.tree.command(name="report", description="輸入主題，自動蒐集相關論文並產生研究報告")
    @discord.app_commands.describe(topic="想研究的主題，例如：multi-agent reinforcement learning")
    async def report_cmd(interaction: discord.Interaction, topic: str):
        if not topic.strip():
            await interaction.response.send_message("用法：`/report 你的主題`", ephemeral=True)
            return
        await interaction.response.defer(thinking=True)
        report, papers = await build_report(topic)
        await interaction.followup.send(
            f"📑 **主題研究報告：{topic}**（取自 arXiv {len(papers)} 篇相關論文）"
        )
        for chunk in _split(report):
            await interaction.channel.send(chunk)

    @bot.tree.command(name="set_push_time", description="設定每日自動推送的時間（24 小時制，本地時區）")
    @discord.app_commands.describe(hour="小時 0-23", minute="分鐘 0-59（預設 0）")
    async def set_push_time_cmd(interaction: discord.Interaction, hour: int, minute: int = 0):
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            await interaction.response.send_message(
                "時間格式錯誤：hour 需 0-23、minute 需 0-59。", ephemeral=True
            )
            return
        _save_schedule(hour, minute)
        daily_task.change_interval(time=_push_time())
        await interaction.response.send_message(
            f"✅ 已設定每日自動推送時間為 **{hour:02d}:{minute:02d}**（UTC+{config.PUSH_TZ_OFFSET}）。"
        )

    @bot.tree.command(name="help", description="顯示 AIR Agent 指令說明")
    async def help_cmd(interaction: discord.Interaction):
        hour, minute = _load_schedule()
        embed = discord.Embed(title="AIR Agent 指令", color=0x4F46E5)
        embed.add_field(name="/daily", value="立即抓取並推送今日 AI 論文", inline=False)
        embed.add_field(name="/ask <問題>", value="依據已收錄論文回答你的問題", inline=False)
        embed.add_field(name="/report <主題>", value="自動蒐集相關論文並產生完整研究報告", inline=False)
        embed.add_field(
            name="/set_push_time <時> <分>",
            value=f"設定每日自動推送時間（目前 {hour:02d}:{minute:02d}，UTC+{config.PUSH_TZ_OFFSET}）",
            inline=False,
        )
        embed.add_field(name="/help", value="顯示這則說明", inline=False)
        await interaction.response.send_message(embed=embed)

    return bot


def _split(text, size=1900):
    """Discord 單則訊息上限 2000 字元，超過則分段。"""
    return [text[i:i + size] for i in range(0, len(text), size)] or [""]
