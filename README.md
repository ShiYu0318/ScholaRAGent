<div align="center">

# RAGency

**RAGency** is a full-stack open-source platform for agentic AI research assistance via
multi-paradigm RAG: it collects papers and news from many sources, answers questions with
streaming cited retrieval and GraphRAG knowledge graphs, runs deep-research agents and
writing tools, and delivers personalized digests, trends, and analytics through a bilingual
web dashboard and Discord bot — one Docker container, SQLite+FAISS or Postgres+pgvector.

[![CI](https://github.com/ShiYu0318/RAGency/actions/workflows/ci.yml/badge.svg)](https://github.com/ShiYu0318/RAGency/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-19-61dafb.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/api-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/tests-389%20passing-brightgreen.svg)](#testing)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Package manager: uv](https://img.shields.io/badge/deps-uv-purple.svg)](https://github.com/astral-sh/uv)

</div>

---

## Table of contents

- [Overview](#overview)
- [Features](#features)
- [Web dashboard](#web-dashboard)
- [RAG design](#rag-design)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
- [API reference](#api-reference)
- [Database schema](#database-schema)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## Overview

RAGency keeps you on top of fast-moving AI research without the daily manual grind. It
gathers the latest papers and community discussion from many sources, distills each item
into a concise summary, and builds a searchable knowledge base you can query in natural
language. Retrieval spans both a dense/sparse vector index and a citation/concept graph, so
the system answers specific questions and reasons about a field as a whole.

The primary interface is an interactive **web dashboard** (React + FastAPI, GitHub-dark
aesthetic, EN/ZH bilingual): streaming Q&A with citations, shareable conversations,
interactive D3 citation/concept graphs, deep-research and writing tools, a reading kanban
with RSS feeds and exports, trend analytics, learning paths, and per-user notification
scheduling. A **Discord bot** remains as a secondary interface sharing the same core, with a
scheduled daily digest and slash commands. User interactions feed a preference reward model
that continuously tunes recommendation ranking.

The project runs on free, local components where possible: **Groq** (OpenAI-compatible) for
generation, **sentence-transformers** for local embeddings, and **FAISS** for vector search.
Heavier options (BGE embeddings and rerankers, HNSW indexing, Postgres + pgvector, OpenAlex
citation data, PDF full-text ingestion) are available behind configuration switches and
degrade gracefully when their services or models are unavailable.

## Features

### Collection and summarization
- **Multi-source collection** — arXiv, AI news (RSS), Hacker News, Reddit, GitHub trending,
  and X/Twitter, plus per-user custom RSS feeds.
- **LLM summarization** — concise, high-signal summaries and key insights for every item.
- **PDF full-text ingestion** — parse arXiv PDFs into titled sections (abstract, method,
  results, and so on) so answers draw on full text, not just abstracts.

### Retrieval and question-answering
- **Hybrid retrieval** — dense vector search (FAISS, optional HNSW) fused with BM25 lexical
  search via Reciprocal Rank Fusion.
- **Query transformation** — HyDE, multi-query rewriting, and question decomposition to widen
  recall.
- **Cross-encoder reranking** — optional BGE reranker for second-stage precision.
- **Parent-document retrieval** — retrieve focused child chunks, return their parent papers.
- **Contextual chunk embedding** — situate each chunk within its document before embedding.
- **Semantic answer cache** — short-circuit near-duplicate questions.
- **Traceable citations** — chunk-level source markers resolve back to paper, section, and
  link, with a citation-accuracy metric to score grounding.

### Graph knowledge base
- **Concept graph** — extract method/dataset/task/metric relations into a directed graph.
- **Community detection and summaries** — cluster the graph into research sub-fields.
- **Citation network** — expand a seed paper into prior (references) and derivative (citing)
  works via OpenAlex, ranked by PageRank influence.
- **Graph retrieval and global search** — neighborhood expansion for specific questions;
  community-report map-reduce for field-level questions.
- **Query routing and adaptive retrieval** — route each question to local or global search
  and choose no-retrieval, single-shot, or multi-step strategies by complexity.

### Reasoning and agents
- **Iterative retrieval agent** — multi-round retrieve-and-decide loops for multi-hop
  questions.
- **Self-reflective retrieval** — assess evidence sufficiency and refine before answering.
- **Corrective retrieval** — fall back to external search when local confidence is low.
- **Deep research mode** — decompose a topic, research each sub-question, and synthesize a
  cited review (streamed live in the dashboard).
- **Multi-agent pipeline** — Planner, Retriever, Writer, and Critic roles with a revision loop.
- **Tool-calling agent** — a natural-language agent that calls local tools for search, trend
  analysis, task management, and calendar export.

### Research workflow tools
- **Literature review** generation with identified research gaps.
- **BibTeX export** with generated citation keys.
- **Method comparison tables** across papers.
- **Guided deep-read** explanations of dense papers.
- **Credibility and impact signals** from citation counts.
- **Reproducibility signals** from linked code repositories.
- **Reading kanban** (to-read / reading / done) with drag-and-drop, and **topic subscriptions**.
- **Obsidian export** — render papers and links as Markdown notes with frontmatter and
  wikilinks for Obsidian, Juggl, and Dataview; CSV and BibTeX exports alongside.
- **Writing assistance** — LaTeX drafts, slide outlines, polishing, contribution extraction,
  review suggestions, and submission checklists.

### Product layer: accounts, delivery, personalization, analytics
- **Multi-account auth** — email + password (bcrypt, JWT), OAuth sign-in with Google and
  GitHub, and Discord account linking.
- **Per-user notification preferences** — frequency (daily/weekly/off), delivery time,
  timezone, quiet hours, channels (web/Telegram/Email/LINE), and dedupe.
- **Per-user scheduling** — an APScheduler-based scheduler cron-schedules each user's digest
  from their preferences and polls due reminders every minute.
- **Weekly digest + trend detection** — LLM-written weekly overview over the freshest papers,
  with rising-keyword detection and next-period forecasting.
- **Contextual reminders** — create, complete, and get notified about research to-dos.
- **Learning paths and skills** — generate step-by-step study plans per topic (LLM with a
  retrieval fallback) and track skill levels.
- **User analytics** — activity timelines, action totals, reading-pipeline counts, and top
  topics from your interaction history.
- **Personalized filtering** — rank the daily firehose against a learned interest profile.
- **Interaction-driven recommendations** — a Bradley-Terry preference reward model learns
  ranking weights from clicks, likes, subscriptions, ratings, and questions.
- **Trend forecasting** — keyword time-series analysis with an LSTM sliding-window forecaster.
- **Health monitoring** — store statistics, scheduler status, and provider-key readiness.

## Web dashboard

| Page | What it does |
| --- | --- |
| **Overview** | Card wall: today's papers, weekly digest, trends, to-read, recent conversations, reading analytics, system health |
| **Ask** | Token-streamed Q&A (SSE) over the library with adaptive retrieval and cited sources |
| **Conversations** | Persistent history with search, rename, delete, and public share links |
| **Research** | Deep research (live streamed decomposition → synthesis), literature review, comparison, report, BibTeX, guided explain |
| **Write** | Polish, contribution extraction, review suggestions, checklist, LaTeX draft, slide outline |
| **Graph** | Interactive D3 citation network (seed expand, click-to-reseed) and concept graph with PageRank and communities; global search; table view fallback |
| **Library** | Paper list with credibility/reproducibility signals, fetch-today, personalized picks, drag-and-drop reading kanban, RSS feed manager, Obsidian/CSV/BibTeX export |
| **Trends** | Rising keywords (slope-ranked), per-keyword time series with forecast, top keywords, data-source status |
| **Learning** | Topic-based learning path generation with checkbox progress; skill levels |
| **Analytics** | Activity bar chart, action totals, reading pipeline, top topics, library totals |
| **Settings** | Account and locale, theme, Google/GitHub link status, Discord linking, notification preferences and schedule, reminders, system/provider status |

Design notes:

- **GitHub-dark aesthetic** — built on [Primer React](https://primer.style/) with
  `ThemeProvider colorMode="night"`: `#0d1117` canvas, `#30363d` borders, `#2f81f7` accent,
  `#238636` primary buttons, 6px radii, 1px hairlines, compact GitHub-like density. A light
  ("day") theme is one toggle away. No emoji, no gradients.
- **Bilingual** — full EN/ZH i18n (react-i18next); locale persists to the user profile.
- **Streaming** — `/api/ask` and `/api/deepresearch` stream over Server-Sent Events; the
  client reads `fetch` streams (POST + Authorization header).
- **Command palette** — press `⌘K` to jump between pages.
- **Auto docs** — the API self-documents at `/docs` (Swagger UI) and `/redoc` (ReDoc).

## RAG design

RAGency implements the major retrieval-augmented generation paradigms as composable
modules:

| Paradigm | Where |
| --- | --- |
| Advanced RAG | hybrid retrieval, query transformation, reranking, parent-document, contextual chunking, caching, traceable citations |
| Modular RAG | `RAGPipeline` composes retrieve/rerank/generate stages into configurable flows |
| GraphRAG | concept graph, community detection, citation network, graph and global search |
| Corrective RAG | external fallback on low retrieval confidence |
| Self-RAG | sufficiency reflection before answering |
| Adaptive RAG | complexity-aware retrieval-depth selection |
| Agentic RAG | iterative retrieval, deep research, multi-agent pipeline |

Evaluation runs on two tracks: deterministic offline metrics (precision@k, recall, MRR,
lexical faithfulness, citation accuracy) for CI-safe regression, and **RAGAS-style
LLM-as-judge metrics** (claim-level faithfulness, answer relevancy, context
precision/recall) implemented natively on the Groq client — no `ragas`/langchain
dependency. `compare_pipelines` scores multiple RAG configurations on a shared golden
dataset for paradigm-comparison experiments.

## Architecture

```
  React + Vite + TS (Primer, EN/ZH)        Discord bot (slash commands + daily schedule)
        |  JWT / SSE                                     |
        v                                                v
  FastAPI (src/api: routers -> services)  <---- shared core (src/): RAG, graph, agents,
        |                                       research tools, recommend, notify, trends
        v
  Store abstraction (src/store)
        |-- SqliteFaissStore    : SQLite + FAISS (local default)
        |-- PostgresPgvectorStore: Postgres + pgvector (deployment)
        |
  APScheduler (per-user digests + reminders) -> notify dispatcher -> Telegram / Email / LINE
        ^
  crawlers (arXiv/news/HN/Reddit/GitHub/X + user RSS) -> LLM summaries -> store + vectors
```

- The **store abstraction** puts users, papers, interactions, conversations, feeds,
  preferences, reminders, learning paths, and vectors behind one interface; the same
  behavior test suite runs against both backends.
- One **service layer** wraps the core modules for the API; every service has an injection
  point (`set_*_service`) so endpoint tests run fully offline.
- Notifications go through a dispatcher that broadcasts only to platforms with configured
  credentials; the rest are skipped automatically.
- External services (OpenAlex, PDF fetching, BGE models, OAuth providers) are wrapped behind
  thin, injectable interfaces so the system stays testable offline and degrades gracefully.

## Tech stack

| Concern | Choice |
| --- | --- |
| LLM | Groq (OpenAI-compatible), default `llama-3.3-70b-versatile`; optional multi-key rotation |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2` default, `BAAI/bge-m3` optional) |
| Reranker | `BAAI/bge-reranker-v2-m3` cross-encoder (optional) |
| Vector store | FAISS (`IndexFlatIP` / `IndexHNSWFlat`) locally; pgvector on Postgres |
| Relational store | SQLite (default) or Postgres, behind a store abstraction |
| API | FastAPI + Uvicorn, SSE streaming, auto Swagger/ReDoc |
| Auth | bcrypt + PyJWT, OAuth (Google/GitHub), Discord account linking |
| Scheduling | APScheduler (per-user cron digests, reminder polling) |
| Frontend | React 19, Vite, TypeScript, Primer React, TanStack Query, react-i18next, D3 |
| Graph | NetworkX (concept and citation graphs, community detection, PageRank) |
| Citations | OpenAlex API (arXiv DOI lookup with title-search fallback) |
| PDF parsing | PyMuPDF |
| Chat platform | `discord.py` (`app_commands` slash commands + `tasks.loop`) |
| Forecasting | PyTorch (LSTM) + NumPy |
| Package manager / deploy | `uv`; Docker multi-stage build + docker-compose; GitHub Actions CI |

## Project structure

Backend and frontend are fully separated; the root holds only cross-cutting
orchestration (Docker, compose, CI).

```
backend/                 Python backend (run all uv commands from here)
  main.py                Entry point: `api` (dashboard), `bot` (Discord), or `all`
  .env                   Secrets and settings (not version-controlled)
  pyproject.toml         Dependencies (uv)
  src/
    config.py            Settings loaded from backend/.env
    config_report.py     Startup readiness and degraded-feature report
    api/                 FastAPI dashboard: app, deps, auth, routers/, services/
    store/               Store abstraction: base, sqlite_faiss, postgres_pgvector
    scheduler.py         Per-user digest/reminder scheduler (APScheduler)
    crawlers/            arxiv, hackernews, github, reddit, news, twitter, openalex
    llm/                 groq_client, key_rotator
    rag/                 embedder, vector_store, chunker, retrievers/, evaluation, ...
    graph/               concept_graph, graph_rag, global_search, citation_network, ...
    agent/               tool_agent, research_agent, deep_research, self_rag, ...
    analysis/            trends, lstm_forecaster
    recommend/           ranker, personalize, reading_list, credibility, ...
    memory/  notify/  tools/  db/  utils/  bot/
  tests/                 Offline deterministic suite + tests/e2e (Playwright, E2E=1)
  data/                  Generated indices, metadata, SQLite database
frontend/                React + Vite + TypeScript + Primer dashboard UI
  src/pages/             Home, Ask, Conversations, Research, Write, Graph, Library,
                         Trends, Learning, Analytics, Settings
  src/components/        Shell, Card, ForceGraph, BarChart, CommandPalette, ...
  src/lib/  src/i18n/    api/auth/sse clients; EN/ZH translations
Dockerfile               Multi-stage build: frontend dist baked into the API image
docker-compose.yml       Single container; optional Postgres via --profile postgres
.github/workflows/       CI: backend tests (with pgvector), frontend build, docker build
```

## Quick start

### Prerequisites

1. Groq API key — https://console.groq.com (free tier works)
2. Python 3.13 + [`uv`](https://github.com/astral-sh/uv), or Docker
3. Discord bot token (optional, only for the bot) — https://discord.com/developers/applications
4. Node.js 22+ (optional, only for frontend development)

### Option 1: Docker Compose (recommended)

Single container — the image bakes the frontend build and FastAPI serves it:

```bash
# 1. Clone the repository
git clone https://github.com/ShiYu0318/RAGency.git
cd RAGency

# 2. Set up environment variables
cp backend/.env.example backend/.env
# Edit backend/.env with your keys (GROQ_API_KEY at minimum)

# 3. Start
docker compose up --build                      # SQLite + FAISS, data in ./backend/data
docker compose --profile postgres up --build   # optional Postgres + pgvector backend

# 4. Access the application
# Web + API:  http://localhost:8000
# API docs:   http://localhost:8000/docs
```

For Postgres, also set `STORE_BACKEND=postgres` and `DATABASE_URL` in `backend/.env`.

### Option 2: Local development

```bash
# Backend (dashboard API)
cd backend
uv sync                     # install dependencies (includes PyTorch; first run is slow)
cp .env.example .env        # then fill in your keys
uv run python main.py api   # dashboard API at :8000 (serves frontend/dist if built)
uv run python main.py bot   # or: the Discord bot
uv run python main.py all   # or: both at once

# Frontend (in another terminal, hot reload; Vite proxies /api to :8000)
cd frontend
npm install
npm run dev                 # UI at http://localhost:5173
```

`uv run` uses the project virtualenv automatically. If you prefer an activated shell:

```bash
source backend/.venv/bin/activate   # then run: python main.py api
```

### First steps

1. Open http://localhost:5173 (dev) or http://localhost:8000 (Docker) and create an
   account — or sign in with Google/GitHub if OAuth keys are configured.
2. Fetch papers: **Library -> Fetch today** pulls and indexes the latest arXiv batch.
3. Ask a question from **Ask** — answers stream in with cited sources.
4. Explore: expand a citation graph in **Graph**, add RSS feeds in **Library -> Feeds**,
   set your digest schedule in **Settings**, and watch **Trends** fill up as the library
   grows.

## Configuration

Settings live in `backend/.env` (never committed). The minimum working configuration:

```bash
# Required — dashboard
GROQ_API_KEY=your-groq-api-key

# Recommended in production
JWT_SECRET=your-secret-key          # openssl rand -hex 32; ephemeral if unset

# Required only for the Discord bot
DISCORD_BOT_TOKEN=your-bot-token
DISCORD_CHANNEL_ID=your-channel-id

# Deployment switches
SCHEDULER_ENABLED=1                 # per-user digests and reminders (compose sets this)
STORE_BACKEND=sqlite                # or postgres (+ DATABASE_URL)
```

Everything else is optional and safely skipped when unset — the full reference:

| Variable | Required | Description |
| --- | :---: | --- |
| `GROQ_API_KEY` | yes | Groq API key ([console.groq.com](https://console.groq.com)) |
| `GROQ_MODEL` | | Model id (default `llama-3.3-70b-versatile`) |
| `DISCORD_BOT_TOKEN` | bot | Discord bot token (required only for the bot) |
| `DISCORD_CHANNEL_ID` | bot | Channel id for the daily push |
| `DISCORD_GUILD_ID` | | Guild id for instant slash-command sync (else global sync) |
| `ARXIV_QUERY` | | arXiv query (default `cat:cs.AI`) |
| `DAILY_COUNT` / `REPORT_COUNT` | | Papers fetched per daily push / per report |
| `PUSH_HOUR` / `PUSH_MINUTE` / `PUSH_TZ_OFFSET` | | Default daily push time and timezone offset |
| `EMBED_MODEL` | | Embedding model (default `all-MiniLM-L6-v2`, or `BAAI/bge-m3`) |
| `INDEX_TYPE` / `HNSW_M` | | Vector index: `flat` (exact) or `hnsw` (approximate) |
| `RERANK_ENABLED` / `RERANK_MODEL` | | Enable BGE cross-encoder reranking |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | | Enable Telegram delivery |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM` / `EMAIL_TO` | | Enable Email delivery |
| `LINE_CHANNEL_TOKEN` / `LINE_TO` | | Enable LINE delivery (Messaging API) |
| `GITHUB_TOKEN` | | Optional, raises GitHub API rate limits |
| `X_BEARER_TOKEN` | | Enables the X/Twitter crawler (X API v2 requires a paid plan) |
| `JWT_SECRET` | | Dashboard auth secret (ephemeral if unset; set it in production) |
| `JWT_EXPIRE_MINUTES` | | Token lifetime (default 7 days) |
| `CORS_ORIGINS` / `API_PUBLIC_URL` / `FRONTEND_URL` | | Dashboard URLs (defaults fit local dev) |
| `GOOGLE/GITHUB/DISCORD_CLIENT_ID/SECRET` | | OAuth sign-in and Discord account linking |
| `STORE_BACKEND` / `DATABASE_URL` | | `sqlite` (default) or `postgres` with pgvector |
| `SCHEDULER_ENABLED` | | Per-user digest/reminder scheduler (compose sets it to 1) |

The arXiv, news, Hacker News, Reddit, and GitHub crawlers work without credentials.
Telegram/Email/LINE delivery, OAuth providers, and the X/Twitter crawler activate only once
their keys are set. Changing `EMBED_MODEL` changes vector dimension; the store detects this
and rebuilds the index automatically.

### Setting up the Discord bot
1. Create an application at the [Discord Developer Portal](https://discord.com/developers/applications).
2. Under **Bot -> Reset Token**, copy the token into `DISCORD_BOT_TOKEN`.
3. Under **OAuth2 -> URL Generator**, select scopes `bot` and `applications.commands`, grant
   `Send Messages`, `Read Message History`, and `Embed Links`, and use the generated URL to
   invite the bot.
4. Enable Developer Mode in Discord to copy the channel and guild IDs.

## Usage

The dashboard is self-explanatory after [First steps](#first-steps); every page is described
in [Web dashboard](#web-dashboard), and the full REST surface in [API reference](#api-reference).

### Discord bot commands

| Command | Description |
| --- | --- |
| `/daily` | Fetch, summarize, and push today's AI papers now |
| `/ask <question>` | Answer from the knowledge base, with cited papers |
| `/deepresearch <topic>` | Decompose a topic and synthesize a cited review |
| `/report <topic>` | Gather relevant papers and generate a structured report |
| `/litreview <topic>` | Generate a literature review with research gaps |
| `/compare <topic>` | Produce a multi-paper method comparison table |
| `/bibtex <topic>` | Collect relevant papers and export BibTeX |
| `/explain <topic>` | Guided deep-read of the most relevant paper |
| `/trends` | Show rising keywords across collected papers |
| `/sources` | Pull trending AI content from HN, GitHub, Reddit, and news |
| `/latex <topic>` | Generate a LaTeX paper draft skeleton |
| `/slides <topic>` | Generate a slide outline |
| `/review <text>` | Get paper-review suggestions |
| `/like <id>` | Mark a paper you like to improve recommendations |
| `/agent <request>` | Natural-language agent that calls tools |
| `/set_push_time <h> <m>` | Set the daily push time (persisted) |
| `/help` | Show command help and current push time |

The daily digest runs automatically at the configured time and is broadcast to every
configured platform.

## API reference

All endpoints are also browsable live at `/docs` (Swagger UI) and `/redoc`. Unless marked
**public**, endpoints require `Authorization: Bearer <JWT>` obtained from register/login or
OAuth. Streaming endpoints return Server-Sent Events (`data: {json}\n\n` frames).

### Auth (`/auth`)

| Method | Path | Description |
| --- | --- | --- |
| POST | `/auth/register` | Create an account (email + password), returns `{token, user}` — public |
| POST | `/auth/login` | Sign in, returns `{token, user}` — public |
| GET | `/auth/me` | Current user profile |
| PATCH | `/auth/me` | Update `display_name`, `locale`, or password |
| GET | `/auth/providers` | Which OAuth providers are configured — public |
| GET | `/auth/oauth/{provider}` | Start Google/GitHub OAuth sign-in (302) — public |
| GET | `/auth/oauth/{provider}/callback` | OAuth callback; redirects to the frontend with a token — public |
| POST | `/auth/discord/link` | Get the Discord account-linking URL |
| DELETE | `/auth/discord/link` | Unlink the Discord account |

### Q&A and conversations (`/api`)

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/ask` | **SSE** — streamed answer over the library; events: `conversation`, `token`, `citations`, `done` |
| GET | `/api/conversations` | List conversations (`?query=` searches titles and messages) |
| GET | `/api/conversations/{id}` | One conversation with messages and citations |
| PATCH | `/api/conversations/{id}` | Rename |
| DELETE | `/api/conversations/{id}` | Delete (204) |
| POST | `/api/conversations/{id}/share` | Create a public share link, returns `{token, url}` |
| GET | `/api/shared/{token}` | Read a shared conversation — public |

### Papers and library (`/api`)

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/papers` | List papers (`?limit=&source=&query=`) with reproducibility signals |
| GET | `/api/paper/{id}` | Paper detail with credibility (OpenAlex) and reproducibility |
| POST | `/api/daily` | Fetch today's arXiv papers, store and index them |
| GET | `/api/daily/personalized` | Papers ranked against your interaction profile |
| POST | `/api/interactions` | Log an interaction (`like`, `click`, ...) for recommendations (201) |
| GET | `/api/reading` | Reading kanban items (`?state=to-read\|reading\|done`) |
| POST | `/api/reading` | Add a paper to the kanban (201) |
| PATCH | `/api/reading/{paper_id}` | Move between states |
| DELETE | `/api/reading/{paper_id}` | Remove from the kanban (204) |
| GET | `/api/export/csv` | Export the library as CSV |
| GET | `/api/export/bibtex` | Export as BibTeX |
| GET | `/api/export/obsidian` | Export as an Obsidian-ready Markdown zip |

### Feeds and subscriptions (`/api`)

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/feeds` | Your RSS feeds |
| POST | `/api/feeds` | Add a feed (201; 409 on duplicate) |
| PATCH | `/api/feeds/{id}` | Update title/category/enabled |
| DELETE | `/api/feeds/{id}` | Remove a feed (204) |
| POST | `/api/feeds/refresh` | Fetch all enabled feeds into the library |
| GET | `/api/subscriptions` | Your keyword subscriptions |
| POST | `/api/subscriptions` | Add a keyword subscription (201) |
| DELETE | `/api/subscriptions/{name}` | Remove one (204) |

### Graph (`/api/graph`)

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/graph/citation?seed=` | Citation network around a seed (arXiv id or title), D3 nodes/edges + PageRank + communities |
| GET | `/api/graph/concept` | Concept graph over the library (`?refresh=1` rebuilds) |
| GET | `/api/graph/global?query=` | Community-summary map-reduce answer for corpus-level questions |

### Research and writing (`/api`)

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/deepresearch` | **SSE** — decompose → per-question research → synthesis; events: `decompose`, `section`, `synthesis`, `citations`, `done` |
| POST | `/api/litreview` | Literature review over retrieved papers |
| POST | `/api/compare` | Multi-paper method comparison table |
| POST | `/api/report` | Structured topic report with citations |
| POST | `/api/bibtex` | BibTeX for retrieved papers |
| POST | `/api/explain` | Guided plain-language deep-read of one paper |
| POST | `/api/write/{tool}` | Writing tools: `polish`, `contributions`, `review`, `checklist`, `latex`, `slides` |

### Insights (`/api`)

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/trends` | Rising keywords (slope-ranked) + top keywords (`?granularity=month\|year&top=`) |
| GET | `/api/trends/{keyword}` | One keyword's time series and next-period forecast |
| GET | `/api/digest/weekly` | Weekly digest: top recent papers, keywords, LLM overview |
| GET | `/api/analytics` | Your activity, action totals, reading pipeline, top topics (`?days=`) |

### Notifications, reminders, learning (`/api`)

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/notifications/preferences` | Your notification preferences |
| PUT | `/api/notifications/preferences` | Update them; the scheduler reschedules immediately |
| GET | `/api/reminders` | Open reminders (`?include_done=true` for all) |
| POST | `/api/reminders` | Create a reminder (201) |
| POST | `/api/reminders/{id}/complete` | Mark done |
| DELETE | `/api/reminders/{id}` | Delete (204) |
| GET | `/api/learning-paths` | Your learning paths |
| POST | `/api/learning-paths` | Generate a path for a topic (LLM, retrieval fallback) (201) |
| PATCH | `/api/learning-paths/{id}` | Update items/progress/topic |
| DELETE | `/api/learning-paths/{id}` | Delete (204) |
| GET | `/api/skills` | Your skill levels |
| PUT | `/api/skills` | Set a skill level (0-100) |

### System and extras (`/api`)

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/health` | Store stats, scheduler status, provider-key readiness (booleans only) — public |
| GET | `/api/sources` | Data-source configuration status |
| GET | `/api/memory` | Your agent memory items (`?kind=&contains=&limit=`) |
| POST | `/api/memory` | Add a memory item (201) |
| POST | `/api/eval` | RAG evaluation — `engine=offline` (default): precision@k, recall, MRR, lexical faithfulness; `engine=judge`: RAGAS-style LLM-judged faithfulness, answer relevancy, context precision/recall (503 without `GROQ_API_KEY`) |
| POST | `/api/agent` | Tool-calling agent (503 without `GROQ_API_KEY`) |

## Database schema

One schema across both store backends (SQLite + FAISS locally, Postgres + pgvector in
deployment), behind the `src/store` abstraction:

```
users                        papers                      interactions
├── id                      ├── id (arXiv id / slug)    ├── id
├── email (unique)          ├── title                   ├── paper_id (FK)
├── password_hash           ├── abstract                ├── user_id
├── google_sub              ├── authors                 ├── action (like/click/ask...)
├── github_id               ├── link                    ├── value
├── discord_id              ├── published               └── created_at
├── display_name            ├── summary
└── locale                  └── source                  paper_embeddings (Postgres)
                                                        ├── paper_id (FK, cascade)
feeds                        user_subscriptions         └── embedding (vector)
├── id                      ├── user_id                    (FAISS index files locally)
├── user_id                 ├── name (unique per user)
├── url (unique per user)   └── keywords (JSON)         notification_preferences
├── title / category                                    ├── user_id (PK)
└── enabled                  reading_list               ├── frequency (daily/weekly/off)
                            ├── user_id + paper_id (PK) ├── hour / minute / timezone
conversations               ├── title / state           ├── quiet_start / quiet_end
├── id                      ├── tags (JSON)             ├── min_score / dedupe
├── user_id                 └── note                    └── channels (JSON)
├── title
├── share_token              reminders                   learning_paths
└── created_at / updated_at ├── id                      ├── id
                            ├── user_id                 ├── user_id
messages                    ├── text                    ├── topic
├── id                      ├── due_at                  ├── items (JSON, checkboxes)
├── conversation_id         ├── context (JSON)          └── progress (JSON)
├── role                    └── done
├── content                                              user_skills
└── citations (JSON)                                    ├── user_id + skill (PK)
                                                        └── level (0-100)
```

## Testing

The full suite is offline and deterministic. It uses a fake embedder, stubbed LLM and network
clients, and injected transports, so no model downloads or credentials are needed. Store
behavior tests also run against Postgres+pgvector when `TEST_DATABASE_URL` is set (CI does
this via a service container), and a Playwright UI smoke suite runs with `E2E=1` against
local dev servers.

```bash
cd backend
uv run pytest                    # 378 passed (postgres/e2e auto-skip locally)
E2E=1 uv run pytest tests/e2e    # UI smoke, needs both dev servers running
```

CI runs the backend suite against a real pgvector service container (389 tests), type-checks
and builds the frontend, and validates the Docker image build on `main`.

## Contributing

1. Fork the repository and create a feature branch: `git checkout -b feature/amazing-feature`
2. Make your changes and add tests (offline stubs; see `backend/tests/` for patterns)
3. Run the checks locally:
   ```bash
   cd backend && uv run pytest -q
   cd frontend && npx tsc --noEmit && npm run build
   ```
4. Commit with a conventional message: `feat(scope): add amazing feature`
5. Push and open a Pull Request — CI must pass (backend + pgvector, frontend, Docker build)

## License

MIT — see [LICENSE](LICENSE).
