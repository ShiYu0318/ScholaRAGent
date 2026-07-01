# AIR-Agent
**AI R**esearch Agent: An autonomous assistant that crawls arXiv papers and AI news, generates LLM summaries, performs RAG retrieval, and delivers insights via multi-platform bots.

---

## Features

- Collects data using web crawlers from the following sources:
  - Latest AI research papers from arXiv
  - AI-related online news
  - Hacker News
  - Technical posts on X (Twitter)
  - Trending discussions on Reddit
  - AI-related GitHub repositories with rapidly growing star counts
- Generates high-quality summaries and extracts key insights from collected content
- Supports multi-paper analysis: retrieves multiple arXiv papers on the same topic and generates a comparative technical report
- Builds a vector knowledge base to answer user queries based on the collected textual data (RAG)
- Provides long-term memory capabilities with memory management, dynamic filtering, and compression
- Pushes the latest updates to Discord / LINE / Telegram / Email. Users can subscribe or interact, and recommendations are dynamically optimized based on user engagement
- Assists users in writing LaTeX research paper drafts, providing review suggestions, and generating presentations or research proposals
- Uses external tools to help users schedule and organize tasks automatically
- Analyzes time-series trends of popular keywords to predict future technology developments

---

## Development Roadmap

| Week | Start Date  | Main Task | Details | Completed |
|-----|------|-----------|--------|-----------|
| 1 | 02/24 | Project Planning | Topic selection, feature brainstorming, architecture design, and project scheduling | [x] |
| 2 | 03/03 | Web Crawler Development | Python Selenium for automated data collection | [x] |
| 3 | 03/10 | Relational Database | Data cleaning and SQLite storage (papers + interactions) | [x] |
| 4 | 03/17 | LLM-based Summarization | LLM API integration and system prompt design | [x] |
| 5 | 03/24 | Discord Bot | discord.py implementation and slash commands | [x] |
| 6 | 03/31 | RAG Implementation | Embeddings, Vector DB (FAISS), chunking, reranking, metadata filtering | [x] |
| 7 | 04/07 | Memory Module | Memory management system and context engineering | [x] |
| 8 | 04/14 | Multi-document Analysis | Compare methods across multiple papers or projects and generate performance comparison tables | [x] |
| 9 | 04/21 | Multi-platform Notifications | LINE Bot, Telegram Bot, Email integration | [x]¹ |
| 10 | 04/28 | Interaction System | Track user behavior: CTR, dwell time, likes, subscriptions, ratings, questions, and shares | [x] |
| 11 | 05/05 | Research Assistant | Generate LaTeX paper drafts, review suggestions, presentations, or research proposals | [x] |
| 12 | 05/12 | MCP / Tool Calling | Function-calling framework + local tools (search, trends, task scheduling) | [x]² |
| 13 | 05/19 | Keyword Trend Prediction | Keyword timeseries + sliding-window forecast (LSTM, plus moving-average / linear) | [x] |
| 14 | 06/02 | RLHF | Bradley–Terry preference reward model learns action weights from pairwise interactions to optimize ranking | [x] |
| 15 | 06/02 | Integration, Optimization, Testing | Module integration and an offline pytest suite (93 tests) | [x] |
| 16 | 06/09 | Final Presentation | Demo and presentation | [ ] |

**Notes**
- ¹ Telegram / Email / LINE adapters and dispatcher are implemented and unit-tested with injected transports; **live delivery needs the user's own tokens/SMTP credentials in `config/.env`** (see SPEC).
- ² Tool-calling uses Groq's OpenAI-compatible function calling with local, credential-free tools. External Google Docs/Calendar can plug into the same registry later.
- Crawlers implemented (all credential-free): arXiv, Hacker News, GitHub-trending, Reddit (public JSON) and AI news (public RSS). **X (Twitter)** remains the only source on the roadmap — no free public read API, so it is credential-gated.
