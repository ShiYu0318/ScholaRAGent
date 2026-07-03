"""Discord bot：每日排程推送論文摘要、RAG 問答、主題研究報告。"""
import asyncio
import json
from datetime import time, timedelta, timezone

import discord
from discord.ext import commands, tasks

from src import config
from src.analysis import trends
from src.crawlers.arxiv_crawler import ArxivCrawler
from src.crawlers.github_crawler import GitHubCrawler
from src.crawlers.hackernews_crawler import HackerNewsCrawler
from src.crawlers.reddit_crawler import RedditCrawler
from src.crawlers.news_crawler import NewsCrawler
from src.crawlers.twitter_crawler import TwitterCrawler
from src.db.database import Database
from src.llm.groq_client import GroqClient
from src.memory.memory_store import MemoryStore
from src.notify import dispatcher
from src.agent.tool_agent import ToolAgent
from src.tools.builtins import build_default_registry
from src.tools.task_manager import TaskManager
from src.rag.vector_store import VectorStore
from src.rag.retrievers.hybrid import HybridRetriever
from src.rag.query_transform import QueryTransformer
from src.rag.retrievers.multi_query import MultiQueryRetriever
from src.rag.retrievers.reranker import CrossEncoderReranker
from src.rag.semantic_cache import SemanticCache
from src.rag.citations import format_citations
from src.agent.deep_research import DeepResearcher
from src.tools.research_tools import to_bibtex, literature_review, explain_paper
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
    hn_crawler = HackerNewsCrawler()
    gh_crawler = GitHubCrawler(token=config.GITHUB_TOKEN or None)
    reddit_crawler = RedditCrawler()
    news_crawler = NewsCrawler()
    twitter_crawler = TwitterCrawler(bearer_token=config.X_BEARER_TOKEN or None)
    llm = GroqClient()
    store = VectorStore()
    db = Database()
    memory = MemoryStore()
    task_manager = TaskManager()
    tool_registry = build_default_registry(store=store, task_manager=task_manager)

    # 進階檢索：混合檢索 + 多查詢改寫；可選 BGE 精排，供 /ask 使用
    hybrid = HybridRetriever(store)
    advanced_retriever = MultiQueryRetriever(QueryTransformer(llm), hybrid.retrieve)
    reranker = CrossEncoderReranker() if config.RERANK_ENABLED else None
    answer_cache = SemanticCache(store.embedder, threshold=0.95)  # 語意快取

    def _advanced_search(question, k=4):
        """多查詢改寫 + 混合檢索（+ 可選 cross-encoder 精排）。每次重建 BM25 索引。"""
        if store.index.ntotal == 0:
            return []
        hybrid.index()
        if reranker is None:
            return advanced_retriever.search(question, k=k)
        # 過取候選再用 cross-encoder 精排到前 k
        cands = advanced_retriever.retrieve(question, k=max(k * 3, 10))
        return [p for p, _ in reranker.rerank(question, cands, k=k)]

    def _persist(papers, source_name="arxiv"):
        """統一寫入向量庫、SQLite 與人類可讀備份。"""
        if not papers:
            return
        store.add(papers)
        db.upsert_papers(papers)
        save_to_text(papers, source_name=source_name)

    async def collect_and_summarize(limit):
        """背景執行緒跑爬蟲＋摘要＋寫入向量庫，回傳含摘要的論文清單。"""
        def _work():
            papers = crawler.fetch_latest_papers(limit=limit)
            for p in papers:
                p["summary"] = llm.summarize(p)
            _persist(papers, source_name="arxiv")
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

    def _digest_text(papers):
        """組出給 Telegram/Email/LINE 的純文字摘要。"""
        lines = [f"今日 AI 論文（{config.ARXIV_QUERY}）"]
        for i, p in enumerate(papers, 1):
            lines.append(f"\n{i}. {p['title']}\n{p.get('summary', p['abstract'])[:200]}\n{p['link']}")
        return "\n".join(lines)

    async def push_daily(channel):
        await channel.send(f"**今日 AI 論文推送**（{config.ARXIV_QUERY}）")
        papers = await collect_and_summarize(config.DAILY_COUNT)
        if not papers:
            await channel.send("今天沒有抓到論文。")
            return
        for p in papers:
            await channel.send(embed=paper_embed(p))
        # 同步廣播到其他已設定的平台（未設定則自動略過）
        results = await asyncio.to_thread(dispatcher.broadcast, _digest_text(papers))
        if results:
            ok = [k for k, v in results.items() if v]
            await channel.send(f"已同步推送到：{', '.join(ok) if ok else '（其他平台發送失敗）'}")
        await channel.send("推送完成，可用 `/ask <問題>` 針對論文發問。")

    async def build_report(topic):
        """背景搜尋主題相關論文、寫入向量庫，並產生研究報告。"""
        def _work():
            papers = crawler.search_topic(topic, limit=config.REPORT_COUNT)
            _persist(papers, source_name="arxiv")
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
        await interaction.response.send_message("開始抓取今日論文…", ephemeral=True)
        await push_daily(interaction.channel)

    @bot.tree.command(name="ask", description="依據已收錄論文回答你的問題")
    @discord.app_commands.describe(question="你想詢問的問題")
    async def ask_cmd(interaction: discord.Interaction, question: str):
        if not question.strip():
            await interaction.response.send_message("用法：`/ask 你的問題`", ephemeral=True)
            return
        await interaction.response.defer(thinking=True)
        cached = answer_cache.get(question)
        if cached is not None:
            papers = []
            answer = cached
        else:
            papers = await asyncio.to_thread(_advanced_search, question, 4)
            body = await asyncio.to_thread(llm.answer, question, papers)
            # 附上可稽核的來源清單，並存入語意快取
            sources = format_citations(papers)
            answer = f"{body}\n\n{sources}" if sources else body
            answer_cache.put(question, answer)
        # 記錄使用者互動與長期記憶（供推薦排序 / 個人化）
        uid = interaction.user.id
        memory.add(uid, question, kind="query")
        for p in papers:
            db.log_interaction("ask", paper_id=p.get("id"), user_id=uid)
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
            f" **主題研究報告：{topic}**（取自 arXiv {len(papers)} 篇相關論文）"
        )
        for chunk in _split(report):
            await interaction.channel.send(chunk)

    @bot.tree.command(name="deepresearch", description="深度研究：拆解子題、逐一檢索並合成含引用的綜述")
    @discord.app_commands.describe(topic="想深入研究的主題")
    async def deepresearch_cmd(interaction: discord.Interaction, topic: str):
        if not topic.strip():
            await interaction.response.send_message("用法：`/deepresearch 你的主題`", ephemeral=True)
            return
        await interaction.response.defer(thinking=True)

        def _deep_retrieve(query, k=4):
            papers = crawler.search_topic(query, limit=k)
            _persist(papers, source_name="arxiv")
            return [(p, 1.0) for p in papers]

        researcher = DeepResearcher(llm, _deep_retrieve, QueryTransformer(llm))
        report, papers = await asyncio.to_thread(researcher.run, topic)
        await interaction.followup.send(
            f" **深度研究：{topic}**（跨 {len(papers)} 篇論文）"
        )
        for chunk in _split(report):
            await interaction.channel.send(chunk)

    @bot.tree.command(name="litreview", description="文獻綜述：蒐集相關論文並生成含研究缺口的綜述草稿")
    @discord.app_commands.describe(topic="想回顧的研究主題")
    async def litreview_cmd(interaction: discord.Interaction, topic: str):
        if not topic.strip():
            await interaction.response.send_message("用法：`/litreview 你的主題`", ephemeral=True)
            return
        await interaction.response.defer(thinking=True)

        def _work():
            papers = crawler.search_topic(topic, limit=config.REPORT_COUNT)
            _persist(papers, source_name="arxiv")
            return literature_review(topic, papers, llm), papers

        review, papers = await asyncio.to_thread(_work)
        await interaction.followup.send(f"**文獻綜述：{topic}**（{len(papers)} 篇）")
        for chunk in _split(review):
            await interaction.channel.send(chunk)

    @bot.tree.command(name="bibtex", description="蒐集相關論文並匯出 BibTeX 引用")
    @discord.app_commands.describe(topic="主題（將取相關論文匯出）")
    async def bibtex_cmd(interaction: discord.Interaction, topic: str):
        if not topic.strip():
            await interaction.response.send_message("用法：`/bibtex 你的主題`", ephemeral=True)
            return
        await interaction.response.defer(thinking=True)

        def _work():
            papers = crawler.search_topic(topic, limit=config.REPORT_COUNT)
            _persist(papers, source_name="arxiv")
            return to_bibtex(papers)

        bib = await asyncio.to_thread(_work)
        for chunk in _split(f"```bibtex\n{bib}\n```"):
            await interaction.channel.send(chunk)

    @bot.tree.command(name="explain", description="深讀導覽：白話講解某主題最相關的一篇論文")
    @discord.app_commands.describe(topic="想弄懂的主題或論文關鍵字")
    async def explain_cmd(interaction: discord.Interaction, topic: str):
        if not topic.strip():
            await interaction.response.send_message("用法：`/explain 主題`", ephemeral=True)
            return
        await interaction.response.defer(thinking=True)

        def _work():
            papers = crawler.search_topic(topic, limit=1)
            _persist(papers, source_name="arxiv")
            if not papers:
                return None, None
            return papers[0], explain_paper(papers[0], llm)

        paper, explanation = await asyncio.to_thread(_work)
        if paper is None:
            await interaction.followup.send("找不到相關論文。")
            return
        await interaction.followup.send(f"**深讀：{paper.get('title', '')}**")
        for chunk in _split(explanation):
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
            f" 已設定每日自動推送時間為 **{hour:02d}:{minute:02d}**（UTC+{config.PUSH_TZ_OFFSET}）。"
        )

    @bot.tree.command(name="compare", description="輸入主題，跨多篇論文產生方法比較表")
    @discord.app_commands.describe(topic="想比較的主題")
    async def compare_cmd(interaction: discord.Interaction, topic: str):
        await interaction.response.defer(thinking=True)
        def _work():
            papers = crawler.search_topic(topic, limit=min(config.REPORT_COUNT, 5))
            _persist(papers, source_name="arxiv")
            return llm.compare_papers(papers), papers
        result, papers = await asyncio.to_thread(_work)
        await interaction.followup.send(f"**多文件比較：{topic}**（{len(papers)} 篇）")
        for chunk in _split(result):
            await interaction.channel.send(chunk)

    @bot.tree.command(name="trends", description="分析已收錄論文的上升關鍵字趨勢")
    async def trends_cmd(interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        rising = await asyncio.to_thread(trends.trending_keywords, store.papers, 10)
        if not rising:
            await interaction.followup.send("目前資料不足以分析趨勢，請先用 `/daily` 或 `/report` 收錄更多論文。")
            return
        lines = [" **上升中的關鍵字**（依成長斜率）"]
        lines += [f"{i}. `{kw}`（斜率 {slope:.2f}）" for i, (kw, slope) in enumerate(rising, 1)]
        await interaction.followup.send("\n".join(lines))

    @bot.tree.command(name="latex", description="依主題產生 LaTeX 論文草稿骨架")
    @discord.app_commands.describe(topic="論文主題")
    async def latex_cmd(interaction: discord.Interaction, topic: str):
        await interaction.response.defer(thinking=True)
        papers = store.search(topic, k=5)
        draft = await asyncio.to_thread(llm.latex_draft, topic, papers)
        await interaction.followup.send(f"**LaTeX 草稿：{topic}**")
        for chunk in _split(f"```latex\n{draft}\n```"):
            await interaction.channel.send(chunk)

    @bot.tree.command(name="slides", description="依主題產生簡報大綱")
    @discord.app_commands.describe(topic="簡報主題")
    async def slides_cmd(interaction: discord.Interaction, topic: str):
        await interaction.response.defer(thinking=True)
        papers = store.search(topic, k=5)
        outline = await asyncio.to_thread(llm.slides_outline, topic, papers)
        await interaction.followup.send(f"**簡報大綱：{topic}**")
        for chunk in _split(outline):
            await interaction.channel.send(chunk)

    @bot.tree.command(name="review", description="貼上段落，取得論文審閱建議")
    @discord.app_commands.describe(text="要審閱的文字")
    async def review_cmd(interaction: discord.Interaction, text: str):
        await interaction.response.defer(thinking=True)
        suggestions = await asyncio.to_thread(llm.review_suggestions, text)
        for chunk in _split(suggestions):
            await interaction.channel.send(chunk)

    @bot.tree.command(name="sources", description="抓取 Hacker News 與 GitHub 上的熱門 AI 內容")
    async def sources_cmd(interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        def _work():
            items = (hn_crawler.fetch_ai_stories(limit=3)
                     + gh_crawler.fetch_trending(limit=3)
                     + reddit_crawler.fetch_ai_discussions(limit_per_sub=2)
                     + news_crawler.fetch_ai_news(limit=3))
            if twitter_crawler.enabled:  # 僅在有 bearer token 時才查 X
                items += twitter_crawler.fetch_recent(limit=3)
            _persist(items, source_name="web")
            return items
        items = await asyncio.to_thread(_work)
        if not items:
            await interaction.followup.send("目前沒有抓到內容（可能是網路或 API 限制）。")
            return
        await interaction.followup.send(f"**HN / GitHub 熱門 AI 內容**（{len(items)} 則）")
        for it in items:
            await interaction.channel.send(f"**[{it['source']}]** {it['title']}\n{it['link']}")

    @bot.tree.command(name="like", description="標記你喜歡的論文（用 arXiv id），用於優化推薦")
    @discord.app_commands.describe(paper_id="論文 id，例如 2401.01234 或 hn-123")
    async def like_cmd(interaction: discord.Interaction, paper_id: str):
        db.log_interaction("like", paper_id=paper_id.strip(), user_id=interaction.user.id, value=3.0)
        await interaction.response.send_message(
            f" 已記錄你對 `{paper_id}` 的喜好，之後推薦會更貼近你的興趣。", ephemeral=True
        )

    @bot.tree.command(name="agent", description="用自然語言請助理查論文、看趨勢或管理待辦（工具呼叫）")
    @discord.app_commands.describe(request="你的請求，例如：幫我找 multi-agent 的論文並加一則待辦")
    async def agent_cmd(interaction: discord.Interaction, request: str):
        await interaction.response.defer(thinking=True)
        agent = ToolAgent(llm.client, tool_registry, config.GROQ_MODEL)
        reply = await asyncio.to_thread(agent.run, request)
        for chunk in _split(reply):
            await interaction.channel.send(chunk)

    @bot.tree.command(name="help", description="顯示 RAGency 指令說明")
    async def help_cmd(interaction: discord.Interaction):
        hour, minute = _load_schedule()
        embed = discord.Embed(title="RAGency 指令", color=0x4F46E5)
        embed.add_field(name="/daily", value="立即抓取並推送今日 AI 論文", inline=False)
        embed.add_field(name="/ask <問題>", value="依據已收錄論文回答你的問題", inline=False)
        embed.add_field(name="/report <主題>", value="自動蒐集相關論文並產生完整研究報告", inline=False)
        embed.add_field(name="/compare <主題>", value="跨多篇論文產生方法比較表", inline=False)
        embed.add_field(name="/trends", value="分析已收錄論文的上升關鍵字趨勢", inline=False)
        embed.add_field(name="/sources", value="抓取 Hacker News 與 GitHub 熱門 AI 內容", inline=False)
        embed.add_field(name="/latex <主題>", value="產生 LaTeX 論文草稿骨架", inline=False)
        embed.add_field(name="/slides <主題>", value="產生簡報大綱", inline=False)
        embed.add_field(name="/review <文字>", value="取得論文審閱建議", inline=False)
        embed.add_field(name="/like <id>", value="標記喜歡的論文以優化推薦", inline=False)
        embed.add_field(name="/agent <請求>", value="自然語言助理，可查論文/看趨勢/管理待辦", inline=False)
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
