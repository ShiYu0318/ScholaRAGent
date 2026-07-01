<div align="center">

# 🤖 AIR-Agent

**AI R**esearch **Agent** — an autonomous research assistant that crawls arXiv papers
and AI news, generates LLM summaries, answers questions over a vector knowledge base (RAG),
and delivers insights through a Discord bot and multi-platform notifications.

[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-102%20passing-brightgreen.svg)](#-testing)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Package manager: uv](https://img.shields.io/badge/deps-uv-purple.svg)](https://github.com/astral-sh/uv)

</div>

---

## 📖 Overview

AIR-Agent keeps you on top of fast-moving AI research without the daily manual grind.
It collects the latest papers and community discussion from multiple sources, distills
each item into a concise summary, and builds a searchable knowledge base you can query in
natural language. A Discord bot delivers a scheduled daily digest and exposes slash commands
for question-answering, topic reports, multi-paper comparison, trend analysis, and
research-writing assistance. User interactions feed a lightweight reward model that
continuously tunes recommendation ranking.

The project runs entirely on free, local components where possible: **Groq** (OpenAI-compatible)
for generation, **sentence-transformers** for local embeddings, and **FAISS** for vector
search — no paid embedding API required.

## ✨ Features

- **Multi-source collection** — arXiv, AI news (RSS), Hacker News, Reddit, GitHub trending
  repositories, and X/Twitter.
- **LLM summarization** — concise, high-signal Traditional-Chinese summaries and key insights
  for every collected item.
- **RAG question-answering** — a FAISS vector knowledge base with chunking, metadata filtering,
  and a two-stage (vector + lexical) reranker; ask questions and get grounded answers with
  cited papers.
- **Topic research reports** — pull the most relevant papers on a topic and generate a
  structured report, stored back into the knowledge base.
- **Multi-document analysis** — compare methods across papers and produce a comparison table.
- **Long-term memory** — per-user memory with dynamic filtering and LLM-based compression to
  keep context bounded.
- **Multi-platform delivery** — scheduled daily push to Discord, plus Telegram, Email, and LINE.
- **Interaction-driven recommendations** — track clicks, likes, subscriptions, ratings, and
  questions; a Bradley–Terry preference reward model learns ranking weights from them.
- **Research assistant** — generate LaTeX paper drafts, review suggestions, and slide outlines.
- **Tool-calling agent** — a natural-language agent that calls local tools to search papers,
  analyze trends, manage tasks, and export calendar events (`.ics`).
- **Trend forecasting** — keyword time-series analysis with an LSTM sliding-window forecaster.

## 🏗️ Architecture

```
                          ┌──────────────── Discord Bot ────────────────┐
  User ──/ask───────────▶ │  RAG retrieval (FAISS) ──▶ Groq answer       │ ──▶ reply (+ cited papers)
  User ──/report────────▶ │  arXiv topic search ────▶ Groq report        │ ──▶ reply (+ vector store)
  User ──/compare───────▶ │  multi-paper ───────────▶ comparison table   │
  User ──/agent─────────▶ │  ToolAgent ─▶ tools (search / trends / tasks / calendar)
                          └───────────────────┬──────────────────────────┘
                                              │  daily schedule (discord.ext.tasks)
                                              ▼
   crawlers (arXiv/news/HN/Reddit/GitHub/X) ─▶ Groq summaries ─▶ FAISS + SQLite ─▶ push
                                                                                 ├─ Discord
                                                                                 ├─ Telegram
                                                                                 ├─ Email
                                                                                 └─ LINE
```

- **FAISS** provides semantic retrieval; **SQLite** provides structured storage for papers and
  interaction events (used by trend analysis and the ranking reward model).
- Notifications go through a dispatcher that broadcasts to whichever platforms have credentials
  configured; the rest are skipped automatically.

## 🧰 Tech Stack

| Concern | Choice |
| --- | --- |
| LLM | Groq (OpenAI-compatible endpoint), default `llama-3.3-70b-versatile` |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`), local & offline |
| Vector store | FAISS (`IndexFlatIP`, cosine via normalized inner product) |
| Relational store | SQLite (standard library) |
| Chat platform | `discord.py` (`app_commands` slash commands + `tasks.loop`) |
| Forecasting | PyTorch (LSTM) + NumPy |
| Package manager | `uv` |

## 📁 Project Structure

```
main.py                      # Entry point: launch the Discord bot
.env                  # Secrets & settings (not version-controlled)
src/
  config.py                  # Loads .env settings
  crawlers/                  # arxiv, hackernews, github, reddit, news (RSS), twitter
  llm/groq_client.py         # summarize / answer / report / compare / latex / review / slides
  rag/                       # embedder, vector_store (scored search + filter + rerank), chunker
  db/database.py             # SQLite: papers + interactions
  memory/memory_store.py     # Long-term memory: filtering + compression
  analysis/                  # trends + lstm_forecaster
  recommend/                 # ranker + reward (preference model)
  notify/                    # telegram, email, line, dispatcher
  tools/                     # registry, builtins, task_manager, calendar_ics
  agent/tool_agent.py        # Function-calling agent loop
  bot/discord_bot.py         # Bot, daily schedule, slash commands
  utils/                     # logger, file_manager
tests/                       # 102 offline tests
data/                        # faiss.index, metadata.json, SQLite db, etc. (generated)
```

## 🚀 Getting Started

### Prerequisites

- Python 3.13
- [`uv`](https://github.com/astral-sh/uv)
- A Groq API key and a Discord bot token (see [Configuration](#-configuration))

### Installation

```bash
uv sync                       # install dependencies (includes PyTorch; first run is slow)
cp .env.example .env   # then fill in your keys (see below)
uv run python main.py         # start the bot
```

## ⚙️ Configuration

Settings live in `.env` (never committed). Required keys are marked; everything else is
optional and safely skipped when unset.

| Variable | Required | Description |
| --- | :---: | --- |
| `GROQ_API_KEY` | ✅ | Groq API key ([console.groq.com](https://console.groq.com)) |
| `GROQ_MODEL` | | Model id (default `llama-3.3-70b-versatile`) |
| `DISCORD_BOT_TOKEN` | ✅ | Discord bot token |
| `DISCORD_CHANNEL_ID` | ✅ | Channel id for the daily push |
| `DISCORD_GUILD_ID` | | Guild id for instant slash-command sync (else global sync) |
| `ARXIV_QUERY` | | arXiv query (default `cat:cs.AI`) |
| `DAILY_COUNT` / `REPORT_COUNT` | | Papers fetched per daily push / per report |
| `PUSH_HOUR` / `PUSH_MINUTE` / `PUSH_TZ_OFFSET` | | Default daily push time and timezone offset |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | | Enable Telegram delivery |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM` / `EMAIL_TO` | | Enable Email delivery |
| `LINE_CHANNEL_TOKEN` / `LINE_TO` | | Enable LINE delivery (Messaging API) |
| `GITHUB_TOKEN` | | Optional, raises GitHub API rate limits |
| `X_BEARER_TOKEN` | | Enables the X/Twitter crawler (X API v2 requires a paid plan) |

> **Credential-gated features.** The arXiv, news, Hacker News, Reddit, and GitHub crawlers work
> without credentials. Telegram/Email/LINE delivery and the X/Twitter crawler are fully
> implemented but only activate once you supply the corresponding keys above. Cloud Google
> Docs/Calendar integration is not included (calendar export is provided locally as `.ics`);
> it can be added behind the existing tool registry via OAuth.

### Setting up the Discord bot

1. Create an application at the [Discord Developer Portal](https://discord.com/developers/applications).
2. Under **Bot → Reset Token**, copy the token into `DISCORD_BOT_TOKEN`.
3. Under **OAuth2 → URL Generator**, select scopes `bot` and `applications.commands`, grant
   `Send Messages`, `Read Message History`, and `Embed Links`, and use the generated URL to
   invite the bot.
4. Enable Developer Mode in Discord to copy the channel/guild IDs.

## 💬 Usage

Once the bot is running and slash commands are synced, the following commands are available:

| Command | Description |
| --- | --- |
| `/daily` | Fetch, summarize, and push today's AI papers now |
| `/ask <question>` | Answer from the knowledge base, with cited papers |
| `/report <topic>` | Gather relevant papers and generate a structured report |
| `/compare <topic>` | Produce a multi-paper method comparison table |
| `/trends` | Show rising keywords across collected papers |
| `/sources` | Pull trending AI content from HN, GitHub, Reddit, and news |
| `/latex <topic>` | Generate a LaTeX paper draft skeleton |
| `/slides <topic>` | Generate a slide outline |
| `/review <text>` | Get paper-review suggestions |
| `/like <id>` | Mark a paper you like to improve recommendations |
| `/agent <request>` | Natural-language agent that calls tools (search, trends, tasks, calendar) |
| `/set_push_time <h> <m>` | Set the daily push time (persisted) |
| `/help` | Show command help and current push time |

The daily digest runs automatically at the configured time and is broadcast to every
configured platform.

## 🧪 Testing

The full suite is offline and deterministic — it uses a fake embedder, stubbed LLM/network
clients, and injected transports, so no model downloads or credentials are needed.

```bash
uv run pytest        # 102 passed
```

## 🗺️ Development Roadmap

| Week | Main Task | Status |
| :---: | --- | :---: |
| 1 | Project planning & architecture | ✅ |
| 2 | Web crawlers (arXiv, news, Hacker News, Reddit, GitHub, X) | ✅ |
| 3 | Relational database (SQLite) | ✅ |
| 4 | LLM-based summarization | ✅ |
| 5 | Discord bot & slash commands | ✅ |
| 6 | RAG (embeddings, FAISS, chunking, rerank, metadata filtering) | ✅ |
| 7 | Memory module (management, filtering, compression) | ✅ |
| 8 | Multi-document analysis & comparison tables | ✅ |
| 9 | Multi-platform notifications (Telegram, Email, LINE) | ✅ |
| 10 | Interaction tracking (clicks, likes, subscriptions, ratings) | ✅ |
| 11 | Research assistant (LaTeX drafts, reviews, slides) | ✅ |
| 12 | Tool-calling framework & local tools (search, trends, tasks, calendar) | ✅ |
| 13 | Keyword trend prediction (LSTM + sliding window) | ✅ |
| 14 | Reward-model ranking from user interactions | ✅ |
| 15 | Integration, optimization, testing | ✅ |
| 16 | Final presentation | ⬜ |

## 📄 License

Released under the [MIT License](LICENSE).
