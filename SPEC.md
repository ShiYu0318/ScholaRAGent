# AIR Agent — MVP SPEC

AI Research Agent 的最小可行性產品（MVP）。

> **核心流程：每日自動抓取最新 AI 論文 → Groq 摘要 → Discord 自動推送 → 使用者用 RAG 問答。**

原始構想（多來源爬蟲、長期記憶、多平台推送、趨勢預測…）規模龐大，本版本聚焦在
一條可展示、可運作的主線，其餘功能維持在 README 的開發路線圖中。

---

## 功能範圍

| 功能 | 說明 |
| --- | --- |
| arXiv 爬蟲 | 用 `arxiv` 官方套件抓取最新 AI 論文（標題／摘要／作者／連結），並可依主題關鍵字檢索 |
| LLM 摘要 | 透過 Groq（OpenAI 相容端點）產生繁體中文重點摘要 |
| Discord 推送 | bot 內建排程，每日固定時間自動把論文摘要發到指定頻道；推送時間可用 `/set_push_time` 隨時調整並持久化 |
| RAG 問答 | 論文摘要存入 FAISS 向量庫，使用者用 `/ask` 斜線指令提問，依據庫內論文回答 |
| 主題研究報告 | 使用者用 `/report <主題>`，bot 自動到 arXiv 找相關重要論文，產出結構化完整報告並收錄進向量庫 |

### 範圍外（暫不實作，保留於 roadmap）
新聞 / Hacker News / Reddit / GitHub 多來源、LINE / Telegram / Email 推送、
長期記憶壓縮、LaTeX 協作、趨勢預測（LSTM）、FastAPI 後端。

---

## 架構

```
使用者 ──/ask────▶ Discord Bot ──▶ RAG 檢索(FAISS) ──▶ Groq 回答 ──▶ 回覆
使用者 ──/report─▶ Discord Bot ──▶ arxiv 主題檢索 ─▶ Groq 撰寫報告 ─▶ 回覆 + 寫入向量庫
                     │
            每日排程 (discord.ext.tasks，時間可由 /set_push_time 調整)
                     ▼
        arxiv 爬蟲 ─▶ Groq 摘要 ─▶ 推送頻道 + 寫入向量庫
```

### 技術選型
- **LLM**：Groq，OpenAI 相容端點，沿用 `openai` 套件，`base_url=https://api.groq.com/openai/v1`，
  預設模型 `llama-3.3-70b-versatile`。
- **爬蟲**：`arxiv` 官方套件。
- **向量化**：本地 `sentence-transformers`（`all-MiniLM-L6-v2`）。
  Groq 不提供 embeddings API，故改用本地模型（免費、離線）。
- **向量庫**：FAISS（`IndexFlatIP`，向量正規化後做內積 = cosine 相似度）。
- **Discord**：`discord.py`（`commands.Bot` + `app_commands` 斜線指令 + `tasks.loop`）。
  斜線指令於 `on_ready` 時 `tree.sync()` 註冊；設定 `DISCORD_GUILD_ID` 可即時同步到指定伺服器（測試用），留空則走全域同步（最久 1 小時生效）。

---

## 專案結構

```
config/.env                      # 金鑰與設定（不進版控）
main.py                          # 進入點：啟動 Discord bot
src/
  config.py                      # 讀取 .env 設定
  crawlers/arxiv_crawler.py      # arxiv 爬蟲：fetch_latest_papers() / search_topic()
  llm/groq_client.py             # Groq 用戶端：summarize() / answer() / research_report()
  rag/embedder.py                # sentence-transformers 包裝
  rag/vector_store.py            # FAISS 建庫 / 存讀 / 檢索 + metadata
  bot/discord_bot.py             # bot、每日排程、指令
  utils/logger.py                # 日誌（沿用）
  utils/file_manager.py          # 人類可讀備份（沿用）
data/                            # faiss.index、metadata.json、schedule.json（執行時生成）
```

---

## 設定（`config/.env`）

```
GROQ_API_KEY=your_groq_key
GROQ_MODEL=llama-3.3-70b-versatile
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_CHANNEL_ID=123456789012345678
DISCORD_GUILD_ID=123456789012345678   # 選填：設定後斜線指令即時同步到該伺服器；留空走全域同步
ARXIV_QUERY=cat:cs.AI
DAILY_COUNT=5
REPORT_COUNT=8       # /report 每次檢索的相關論文數
PUSH_HOUR=9          # 預設推送「時」（本地時區）
PUSH_MINUTE=0        # 預設推送「分」（本地時區）
PUSH_TZ_OFFSET=8     # 時區偏移（小時），+8 = 台灣
```

> 推送時間以本地時區（`PUSH_TZ_OFFSET`）表示。`.env` 的 `PUSH_HOUR/PUSH_MINUTE` 只是預設值；
> 使用者用 `/set_push_time` 設定後會寫入 `data/schedule.json`，重啟後仍生效並覆蓋預設值。

### 取得 Groq API Key
1. 前往 <https://console.groq.com> 註冊登入。
2. 左側 **API Keys** → **Create API Key** → 複製貼到 `GROQ_API_KEY`。

### 建立 Discord Bot
1. 前往 <https://discord.com/developers/applications> → **New Application**。
2. 左側 **Bot** → **Reset Token** 取得 token，填入 `DISCORD_BOT_TOKEN`。
   （斜線指令不需開啟 MESSAGE CONTENT INTENT。）
3. **OAuth2 → URL Generator**：scope 同時勾選 `bot` 與 **`applications.commands`**
   （缺少 `applications.commands` 斜線指令不會出現），權限勾 `Send Messages`、
   `Read Message History`、`Embed Links`，用產生的 URL 把 bot 邀請進你的伺服器。
4. 在 Discord 開啟「開發者模式」(設定→進階)，右鍵目標頻道→複製 ID，填入 `DISCORD_CHANNEL_ID`；
   右鍵伺服器→複製伺服器 ID，可填入 `DISCORD_GUILD_ID` 讓斜線指令即時同步。

---

## 指令

| 指令 | 功能 |
| --- | --- |
| `/daily` | 立即抓取今日論文、摘要並推送（demo 用，不必等排程） |
| `/ask <問題>` | 依向量庫內論文用 Groq 回答，附參考論文標題 |
| `/report <主題>` | 自動到 arXiv 找該主題的相關重要論文，產出結構化研究報告並收錄進向量庫 |
| `/set_push_time <時> <分>` | 設定每日自動推送時間（24 小時制、本地時區），即時生效並持久化 |
| `/help` | 顯示用法與目前推送時間 |

均為斜線（slash）指令，於 bot 啟動時自動向 Discord 同步註冊。
排程：每日於設定時間（預設 `PUSH_HOUR:PUSH_MINUTE`）自動執行 `/daily` 的內容；
`/set_push_time` 會透過 `tasks.loop.change_interval` 即時改排程並寫入 `schedule.json`。

---

## 安裝與執行

```bash
uv sync                      # 安裝依賴（含 PyTorch，首次較久）
# 填好 config/.env
uv run python main.py        # 啟動 bot
```

---

## 驗證（end-to-end）
1. `uv sync` 成功。
2. 啟動 bot，日誌出現「已同步 N 個斜線指令」；在 Discord 輸入 `/` 可看到 `daily`/`ask`/`help`。
3. 執行 `/daily` → 出現數篇含繁中摘要的論文 Embed，`data/` 生成向量庫檔。
4. 執行 `/ask 有哪些關於 multi-agent 的論文?` → 得到依據當日論文的回答與參考標題。
5. 執行 `/report multi-agent reinforcement learning` → 得到含「主題概述／重點論文／趨勢／總結」的報告。
6. 執行 `/set_push_time 9 30` → 回覆已設定 09:30，`data/schedule.json` 生成；用 `/help` 確認顯示新時間。
7. 將推送時間設為近一兩分鐘後，驗證自動推送觸發。
