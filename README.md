<div align="center">

# AIR-Agent

**AI Research Agent** — an autonomous research assistant that collects papers and AI news
from multiple sources, summarizes them with an LLM, answers questions over a vector and
graph knowledge base, and delivers everything through a Discord bot and multi-platform
notifications.

[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-298%20passing-brightgreen.svg)](#testing)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Package manager: uv](https://img.shields.io/badge/deps-uv-purple.svg)](https://github.com/astral-sh/uv)

</div>

---

## Overview

AIR-Agent keeps you on top of fast-moving AI research without the daily manual grind. It
gathers the latest papers and community discussion from many sources, distills each item
into a concise summary, and builds a searchable knowledge base you can query in natural
language. Retrieval spans both a dense/sparse vector index and a citation/concept graph, so
the system answers specific questions and reasons about a field as a whole.

A Discord bot delivers a scheduled daily digest and exposes slash commands for
question-answering, deep research, literature review, multi-paper comparison, trend
analysis, and writing assistance. User interactions feed a preference reward model that
continuously tunes recommendation ranking.

The project runs on free, local components where possible: **Groq** (OpenAI-compatible) for
generation, **sentence-transformers** for local embeddings, and **FAISS** for vector search.
Heavier options (BGE embeddings and rerankers, HNSW indexing, OpenAlex citation data, PDF
full-text ingestion) are available behind configuration switches and degrade gracefully when
their services or models are unavailable.

## Features

### Collection and summarization
- **Multi-source collection** — arXiv, AI news (RSS), Hacker News, Reddit, GitHub trending,
  and X/Twitter.
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
  cited review.
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
- **Reading kanban** (to-read / reading / done) and **topic subscriptions**.
- **Obsidian export** — render papers and links as Markdown notes with frontmatter and
  wikilinks for Obsidian, Juggl, and Dataview.
- **Writing assistance** — LaTeX drafts, slide outlines, polishing, contribution extraction,
  and submission checklists.

### Delivery, personalization, and analysis
- **Multi-platform delivery** — scheduled daily push to Discord, plus Telegram, Email, LINE.
- **Personalized filtering** — rank the daily firehose against a learned interest profile.
- **Interaction-driven recommendations** — a Bradley-Terry preference reward model learns
  ranking weights from clicks, likes, subscriptions, ratings, and questions.
- **Trend forecasting** — keyword time-series analysis with an LSTM sliding-window forecaster.

## RAG design

AIR-Agent implements the major retrieval-augmented generation paradigms as composable
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

## Architecture

```
                        Discord bot (slash commands + daily schedule)
  user question ->  route by complexity/scope -> retrieve -> generate -> reply (+ sources)
                          |                          |
                          |                          +-- vector (FAISS/HNSW) + BM25 fusion
                          |                          +-- graph (concept / citation network)
                          |
  crawlers (arXiv/news/HN/Reddit/GitHub/X) -> LLM summaries -> FAISS + SQLite -> daily push
                                                                              |-- Discord
                                                                              |-- Telegram
                                                                              |-- Email
                                                                              |-- LINE
```

- **FAISS** provides semantic retrieval; **SQLite** stores papers and interaction events used
  by trend analysis and the ranking reward model.
- Notifications go through a dispatcher that broadcasts only to platforms with configured
  credentials; the rest are skipped automatically.
- External services (OpenAlex, PDF fetching, BGE models) are wrapped behind thin, injectable
  interfaces so the system stays testable offline and degrades gracefully.

## Tech stack

| Concern | Choice |
| --- | --- |
| LLM | Groq (OpenAI-compatible), default `llama-3.3-70b-versatile`; optional multi-key rotation |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2` default, `BAAI/bge-m3` optional) |
| Reranker | `BAAI/bge-reranker-v2-m3` cross-encoder (optional) |
| Vector store | FAISS, exact `IndexFlatIP` or approximate `IndexHNSWFlat` (inner product) |
| Graph | NetworkX (concept and citation graphs, community detection, PageRank) |
| Citations | OpenAlex API (arXiv DOI lookup with title-search fallback) |
| PDF parsing | PyMuPDF |
| Relational store | SQLite (standard library) |
| Chat platform | `discord.py` (`app_commands` slash commands + `tasks.loop`) |
| Forecasting | PyTorch (LSTM) + NumPy |
| Package manager | `uv` |

## Project structure

```
main.py                  Entry point: launch the Discord bot
.env                     Secrets and settings (not version-controlled)
src/
  config.py              Settings loaded from .env
  config_report.py       Startup readiness and degraded-feature report
  crawlers/              arxiv, hackernews, github, reddit, news, twitter, openalex
  llm/                   groq_client, key_rotator
  rag/                   embedder, vector_store, chunker, contextual, semantic_cache,
                         citations, chunk_citations, evaluation, eval_harness,
                         caching_embedder, pipeline, pdf_ingest, testset_builder,
                         query_transform, retrievers/ (bm25, hybrid, multi_query,
                         reranker, parent)
  graph/                 concept_graph, graph_rag, global_search, router, relationship,
                         citation_network, visualize
  agent/                 tool_agent, research_agent, self_rag, deep_research, multi_agent,
                         corrective_rag, adaptive_rag
  analysis/              trends, lstm_forecaster
  recommend/             ranker, reward, personalize, reading_list, subscriptions,
                         reproducibility, credibility
  memory/                memory_store
  notify/                telegram, email, line, dispatcher
  tools/                 registry, builtins, task_manager, calendar_ics, research_tools,
                         obsidian_export
  db/                    database
  utils/                 logger, file_manager, query_log
  bot/                   discord_bot
tests/                   Offline, deterministic test suite (298 tests)
data/                    Generated indices, metadata, SQLite database
```

## Getting started

### Prerequisites
- Python 3.13
- [`uv`](https://github.com/astral-sh/uv)
- A Groq API key and a Discord bot token (see [Configuration](#configuration))

### Installation

```bash
uv sync                     # install dependencies (includes PyTorch; first run is slow)
cp .env.example .env        # then fill in your keys
uv run python main.py       # start the bot
```

### Web dashboard

A full-stack dashboard (FastAPI + React/Vite/TypeScript + Primer, EN/ZH) covers streaming
Q&A with citations, conversations and sharing, interactive D3 citation/concept graphs, deep
research, writing tools, a reading kanban with RSS feeds and exports, trends, learning paths,
analytics, and per-user notification scheduling. Design notes live in `docs/ui-dashboard-plan.md`.

Development mode (two processes, Vite proxies `/api` to `:8000`):

```bash
uv run uvicorn src.api.app:app --port 8000    # API + Swagger at /docs
cd frontend && npm install && npm run dev      # UI at http://localhost:5173
```

Single-container deployment (the image bakes the frontend build; FastAPI serves it):

```bash
docker compose up --build                      # SQLite + FAISS, data in ./data
docker compose --profile postgres up --build   # optional Postgres + pgvector backend
```

For Postgres, set `STORE_BACKEND=postgres` and `DATABASE_URL` in `.env`
(see `.env.example` for all dashboard variables: JWT, OAuth providers, scheduler).

## Configuration

Settings live in `.env` (never committed). Required keys are marked; everything else is
optional and safely skipped when unset.

| Variable | Required | Description |
| --- | :---: | --- |
| `GROQ_API_KEY` | yes | Groq API key ([console.groq.com](https://console.groq.com)) |
| `GROQ_MODEL` | | Model id (default `llama-3.3-70b-versatile`) |
| `DISCORD_BOT_TOKEN` | yes | Discord bot token |
| `DISCORD_CHANNEL_ID` | yes | Channel id for the daily push |
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
| `GOOGLE/GITHUB/DISCORD_CLIENT_ID/SECRET` | | OAuth sign-in and Discord account linking |
| `STORE_BACKEND` / `DATABASE_URL` | | `sqlite` (default) or `postgres` with pgvector |
| `SCHEDULER_ENABLED` | | Per-user digest/reminder scheduler (compose sets it to 1) |

The arXiv, news, Hacker News, Reddit, and GitHub crawlers work without credentials.
Telegram/Email/LINE delivery and the X/Twitter crawler activate only once their keys are set.
Changing `EMBED_MODEL` changes vector dimension; the store detects this and rebuilds the index
automatically.

### Setting up the Discord bot
1. Create an application at the [Discord Developer Portal](https://discord.com/developers/applications).
2. Under **Bot -> Reset Token**, copy the token into `DISCORD_BOT_TOKEN`.
3. Under **OAuth2 -> URL Generator**, select scopes `bot` and `applications.commands`, grant
   `Send Messages`, `Read Message History`, and `Embed Links`, and use the generated URL to
   invite the bot.
4. Enable Developer Mode in Discord to copy the channel and guild IDs.

## Usage

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

## Testing

The full suite is offline and deterministic. It uses a fake embedder, stubbed LLM and network
clients, and injected transports, so no model downloads or credentials are needed. Store
behavior tests also run against Postgres+pgvector when `TEST_DATABASE_URL` is set (CI does
this via a service container), and a Playwright UI smoke suite runs with `E2E=1` against
local dev servers.

```bash
uv run pytest                    # 378 passed (postgres/e2e auto-skip locally)
E2E=1 uv run pytest tests/e2e    # UI smoke, needs both dev servers running
```

## License

Released under the [MIT License](LICENSE).
