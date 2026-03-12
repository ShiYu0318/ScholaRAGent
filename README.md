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
| 3 | 03/10 | Relational Database | Data cleaning and PostgreSQL storage | [ ] |
| 4 | 03/17 | LLM-based Summarization | LLM API integration and system prompt design | [ ] |
| 5 | 03/24 | Discord Bot | discord.py implementation and slash commands | [ ] |
| 6 | 03/31 | RAG Implementation | Embeddings, Vector DB (FAISS), chunking, reranking, metadata filtering | [ ] |
| 7 | 04/07 | Memory Module | Memory management system and context engineering | [ ] |
| 8 | 04/14 | Multi-document Analysis | Compare methods across multiple papers or projects and generate performance comparison tables | [ ] |
| 9 | 04/21 | Multi-platform Notifications | LINE Bot, Telegram Bot, Email integration | [ ] |
| 10 | 04/28 | Interaction System | Track user behavior: CTR, dwell time, likes, subscriptions, ratings, questions, and shares | [ ] |
| 11 | 05/05 | Research Assistant | Generate LaTeX paper drafts, review suggestions, presentations, or research proposals | [ ] |
| 12 | 05/12 | MCP / Tool Calling | Integrate external tools such as Google Docs, Calendar, Email, etc. | [ ] |
| 13 | 05/19 | Keyword Trend Prediction | Use LSTM and sliding window for forecasting future technology trends | [ ] |
| 14 | 06/02 | RLHF | Design reward functions based on user interactions to dynamically optimize recommendations and ranking weights | [ ] |
| 15 | 06/02 | Integration, Optimization, Testing | Module integration, performance optimization, and system testing | [ ] |
| 16 | 06/09 | Final Presentation | Demo and presentation | [ ] |
