# AIR-Agent 儀表板 — 前端設計規劃（v2 / E5）

> 定位：研究員／研究生的「研究駕駛艙」，補足 Discord 之外的可視化體驗。
> 原型：`frontend/prototype.html`（單檔、可直接開，展示美學方向與星圖互動）。

## 一、美學方向：Observatory（天文台 / 星圖）

研究工具不做罐頭 SaaS。核心隱喻＝**把研究領域當成一片可導航的星空**：
論文＝星、被引數＝亮度、研究社群＝星雲、引用關係＝星座連線。
整體像一台夜間精密觀測儀器——適合長時間閱讀、資訊密集但不吵。

- **主題**：暗色，深夜墨藍 `#080B13` 底 + 羊皮紙暖白 `#ECE5D6` 文字
- **訊號色**：琥珀金 `#F2A93B`（主行動/星）、青綠 `#5FD6C6`（連線/GraphRAG）、
  紫 `#8E7BE6`、玫瑰 `#E67B93`（區分四個研究社群）
- **氛圍**：星雲徑向漸層 + 噪點顆粒（SVG turbulence）+ 玻璃模糊面板
- **記憶點**：中央 **canvas 星圖**——twinkle 動畫、hover 點亮同社群星座、tooltip

## 二、字體（刻意避開 AI 罐頭味）

| 用途 | 字體 | 理由 |
|---|---|---|
| Display 標題 | **Fraunces**（opsz 光學襯線）| 學術/期刊氣質、有個性 |
| UI 介面 | **Spline Sans** | 現代但不像 Inter/Roboto |
| 數據/代碼 | **IBM Plex Mono** | 引用編號、指標、⌘K |

> 明確不用：Inter、Roboto、Arial、system-ui、Space Grotesk（過度氾濫）。

## 三、版面（3×3 grid，非對稱駕駛艙）

```
┌──────┬─────────────────────┬──────────┐
│      │  ⌘K 指令列 · 狀態    │          │
│ 左軌 ├─────────────────────┤ 右面板   │
│ 導覽 │   ★ 研究星圖 canvas  │ 選中論文 │
│      │   (社群/引用/hover)  │ +答案來源│
│      ├─────────────────────┤ +閱讀看板│
│      │  趨勢 sparkline 帶   │          │
└──────┴─────────────────────┴──────────┘
```

- **左軌**：星圖 / 每日論文 / 文獻綜述 / 比較表 / 閱讀看板 / 趨勢 / 設定
- **⌘K 指令列**：一個入口打通 `/ask`、搜尋論文（對標 Raycast/Linear）
- **中央星圖**：GraphRAG 的視覺出口（對應 C5 研究地圖）
- **右面板**：論文詳情 + **答案來源逐句標註**（對應 A5）+ 閱讀看板（D7）
- **底部**：熱詞 sparkline（對應 A 軌 LSTM 趨勢，已有資料）
- **載入**：交錯淡入（staggered rise），一次到位不浮誇

## 四、技術落地建議

| 面向 | 選型 | 備註 |
|---|---|---|
| 框架 | **React + Vite + TypeScript** | SPA，對接 FastAPI |
| 後端 | **FastAPI**（新增，包現有 `src/`）| REST + SSE 串流問答 |
| 星圖/圖 | **react-force-graph**（WebGL）或 sigma.js | 大圖效能；原型用純 canvas 手刻示意 |
| 圖表 | **visx** 或 lightweight-charts | 趨勢/sparkline |
| 動效 | **Motion**（framer-motion）| 進場編排、微互動 |
| 樣式 | CSS 變數 + Tailwind（或 vanilla）| 主題 token 化 |
| 狀態/資料 | TanStack Query | 快取後端查詢 |

### 建議後端 API 合約（草案）
```
GET  /api/graph?topic=...        → {nodes:[{id,title,cite,cluster,x,y}], edges:[{s,t}]}
POST /api/ask        {question}  → SSE: token 串流 + 末端 citations[]
GET  /api/daily                  → 個人化排序後的今日論文（D11）
GET  /api/trends                 → 熱詞 + LSTM 預測（已有）
GET  /api/reading                → 閱讀看板狀態（D7）
POST /api/reading    {id,state}  → 更新看板
GET  /api/compare?ids=...        → 方法×資料集×指標比較表（D4）
```
以上皆薄封裝現有 `src/` 模組；缺外部服務時回退（與離線測試一致）。

## 五、對應路線圖 phase
星圖↔C5、答案來源↔A5、指令列問答↔A2/B、閱讀看板↔D7、趨勢↔A 軌、比較表↔D4、每日個人化↔D11。
→ 前端本身列為 **E5**，建議在 C 軌（GraphRAG）有資料後再全面實作；現階段先定調美學＋原型。

## 六、下一步選項
1. 把原型擴充成真正的 React + Vite 專案骨架（元件化、路由、mock 資料）。
2. 先做 **FastAPI 後端 + `/api/ask` SSE**，讓原型接真實資料。
3. 維持原型定調，優先回 A3（BGE reranker）等後端 phase，前端等 GraphRAG 就緒。
