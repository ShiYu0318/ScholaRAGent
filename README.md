# AIR-Agent
AI Research Agent: An autonomous assistant that crawls arXiv papers and AI news, generates LLM summaries, performs RAG retrieval, and delivers insights via multi-platform bots.

---

## Feature

- 運用爬蟲蒐集以下資料
    - arXiv 最新 AI 領域論文
    - AI 網路新聞
    - Hacker News 
    - X 技術文章
    - Reddit 社群討論趨勢
    - GitHub Star 數量快速成長的 AI 相關專案
- 進行高品質摘要與重點萃取與統整
- 能針對一個主題同時抓取多篇 arXiv 論文分析並生成一份技術對比報告
- 建立向量知識庫，針對使用者的問題查詢蒐集的文本內容據實回覆
- 具備長期記憶能力，並能管理記憶，動態篩選與壓縮
- 將最新資訊推送到 Discord / LINE / Telegram / Email，使用者可訂閱或互動，並根據自動蒐集的使用者互動狀況動態優化推薦內容
- 協助使用者以 LaTeX 撰寫論文初稿、審稿建議、生成簡報或研究計劃 
- 使用外部工具直接幫使用者排程規劃
- 分析熱門關鍵字時間序列，預測未來科技發展方向


---

## 進度規劃

| 週次 | 日期   | 主要內容               | 詳細內容                                                                 | 完成  |
|------|--------|------------------------|------------------------------------------------------------------------|-------|
| 1    | 02/24  | 專案構思               | 主題訂定、功能發想、架構設計、進度規劃                                  | TRUE  |
| 2    | 03/03  | 爬蟲開發               | Python Selenium、自動化蒐集資料                                         | TRUE  |
| 3    | 03/10  | 關聯式資料庫           | 資料清理、PostgreSQL 存取                                              | FALSE |
| 4    | 03/17  | LLM 摘要生成           | LLM API 串接、System Prompt 設計                                       | FALSE |
| 5    | 03/24  | Discord Bot            | discord.py、slash command                                              | FALSE |
| 6    | 03/31  | RAG                    | Embedding、Vector DB (FAISS)、chunking、reranking、metadata filtering | FALSE |
| 7    | 04/07  | 記憶模組               | 記憶管理系統、上下文工程                                              | FALSE |
| 8    | 04/14  | 多文件分析比較         | 分析多篇論文或專案方法比較、生成性能差異表格                            | FALSE |
| 9    | 04/21  | 多平台推播             | LINE Bot、Telegram Bot、Email                                         | FALSE |
| 10   | 04/28  | 互動系統               | 記錄使用者行為：點擊率、停留時間、按讚、訂閱、評分、提問、分享         | FALSE |
| 11   | 05/05  | 研究助理               | LaTeX 撰寫論文初稿、審稿建議、生成簡報或研究計劃                       | FALSE |
| 12   | 05/12  | MCP / Tool Calling     | 外部工具：Google Docs、Calendar、Email、etc.                           | FALSE |
| 13   | 05/19  | 關鍵字趨勢預測未來發展 | LSTM、Sliding Window                                                   | FALSE |
| 14   | 05/26  | RLHF                   | 根據使用者互動狀況設計 Reward Function 動態優化推薦內容與調整權重排序 | FALSE |
| 15   | 06/02  | 整合＆優化＆測試       | 模組整合、效能優化、系統測試                                          | FALSE |
| 16   | 06/09  | 期末報告               | 簡報＆Demo                                                             | FALSE |