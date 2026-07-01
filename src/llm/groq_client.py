"""Groq 用戶端（OpenAI 相容端點）：論文摘要與 RAG 問答。"""
from openai import OpenAI

from src import config
from src.utils.logger import get_logger


class GroqClient:
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.model = config.GROQ_MODEL
        self.client = OpenAI(
            api_key=config.GROQ_API_KEY,
            base_url=config.GROQ_BASE_URL,
        )

    def _chat(self, system, user, temperature=0.3, max_tokens=800):
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content.strip()

    def summarize(self, paper):
        """產生一篇論文的繁體中文重點摘要（2-3 句）。"""
        system = (
            "你是 AI 研究助理。請用繁體中文，以 2-3 句話精煉地摘要論文的核心貢獻，"
            "聚焦在它解決什麼問題、提出什麼方法。不要客套話，直接給重點。"
        )
        user = f"標題：{paper['title']}\n\n摘要：{paper['abstract']}"
        try:
            return self._chat(system, user, max_tokens=300)
        except Exception as e:
            self.logger.error(f"摘要失敗: {e}")
            return "（摘要產生失敗）"

    def answer(self, question, papers):
        """依據檢索到的論文回答問題。"""
        if not papers:
            return "目前知識庫沒有相關論文，請先用 `/daily` 抓取論文。"

        context = "\n\n".join(
            f"[{i}] 標題：{p['title']}\n摘要：{p['abstract']}\n連結：{p['link']}"
            for i, p in enumerate(papers, 1)
        )
        system = (
            "你是 AI 研究助理。請『僅根據』以下提供的論文內容，用繁體中文回答使用者問題。"
            "若提供內容不足以回答，請誠實說明。回答結尾以「參考論文：」列出你引用的論文標題。"
        )
        user = f"=== 論文資料 ===\n{context}\n\n=== 問題 ===\n{question}"
        try:
            return self._chat(system, user, max_tokens=1000)
        except Exception as e:
            self.logger.error(f"問答失敗: {e}")
            return f"回答時發生錯誤：{e}"

    def research_report(self, topic, papers):
        """針對指定主題，根據檢索到的論文產生完整性研究報告。"""
        if not papers:
            return f"找不到與「{topic}」相關的論文，請換個關鍵字或稍後再試。"

        context = "\n\n".join(
            f"[{i}] 標題：{p['title']}\n作者：{p['authors']}\n發表：{p['published']}\n"
            f"摘要：{p['abstract']}\n連結：{p['link']}"
            for i, p in enumerate(papers, 1)
        )
        system = (
            "你是資深 AI 研究分析師。請『僅根據』以下提供的論文，用繁體中文撰寫一份結構化的主題研究報告。"
            "報告需包含下列段落（用 Markdown 標題）：\n"
            "## 主題概述：用 3-4 句說明此主題在做什麼、為何重要。\n"
            "## 重點論文：逐篇條列，每篇一行說明其核心貢獻與方法。\n"
            "## 研究趨勢與共通點：歸納這些論文反映的技術方向、方法演進或尚未解決的問題。\n"
            "## 總結：2-3 句的整體觀察與建議延伸閱讀方向。\n"
            "請務實、聚焦重點，不要客套話。引用論文時用編號 [n] 對應，最後附「參考論文：」列出標題與連結。"
        )
        user = f"=== 主題 ===\n{topic}\n\n=== 論文資料 ===\n{context}"
        try:
            return self._chat(system, user, temperature=0.4, max_tokens=2000)
        except Exception as e:
            self.logger.error(f"產生報告失敗: {e}")
            return f"產生報告時發生錯誤：{e}"

    def compare_papers(self, papers):
        """跨多篇論文做方法比較，產出 Markdown 比較表 + 分析（Week8）。"""
        if len(papers) < 2:
            return "多文件比較至少需要 2 篇論文，請先用 `/report` 或 `/daily` 收錄更多論文。"

        context = "\n\n".join(
            f"[{i}] 標題：{p['title']}\n作者：{p.get('authors', '')}\n"
            f"發表：{p.get('published', '')}\n摘要：{p['abstract']}"
            for i, p in enumerate(papers, 1)
        )
        system = (
            "你是資深 AI 研究分析師。請『僅根據』以下論文，用繁體中文產出一份多文件比較分析。"
            "格式需求：\n"
            "1. 先給一個 Markdown 表格，欄位為：| 論文 | 解決的問題 | 核心方法 | 主要優勢 | 限制/前提 |，"
            "每篇論文一列，內容精煉（各格 20 字內）。\n"
            "2. 表格後用 ## 綜合比較 段落，指出這些方法的共通點、關鍵差異與取捨。\n"
            "3. 最後用 ## 選用建議 說明在什麼情境下該選哪一種方法。\n"
            "務實、聚焦，不要客套話。論文以編號 [n] 對應。"
        )
        user = f"=== 待比較論文 ===\n{context}"
        try:
            return self._chat(system, user, temperature=0.4, max_tokens=2000)
        except Exception as e:
            self.logger.error(f"比較分析失敗: {e}")
            return f"產生比較分析時發生錯誤：{e}"

    # ---- 研究助理（Week11）----
    def latex_draft(self, topic, papers=None):
        """產生一份可編譯的 LaTeX 論文草稿骨架（含相關工作段落）。"""
        refs = ""
        if papers:
            refs = "\n".join(f"- {p['title']}（{p.get('link', '')}）" for p in papers)
        system = (
            "你是學術寫作助手。請輸出一份『可直接編譯』的 LaTeX 論文草稿，使用 article 類別，"
            "包含 \\title、\\author、\\begin{abstract}、以及 Introduction / Related Work / "
            "Method / Experiments / Conclusion 各 \\section 與占位內容。"
            "內文用英文，摘要 3-4 句。只輸出 LaTeX 原始碼，不要額外說明或 Markdown 圍欄。"
        )
        user = f"Topic: {topic}"
        if refs:
            user += f"\n\n可參考的相關論文：\n{refs}"
        try:
            return self._chat(system, user, temperature=0.5, max_tokens=1800)
        except Exception as e:
            self.logger.error(f"LaTeX 草稿失敗: {e}")
            return f"產生 LaTeX 草稿時發生錯誤：{e}"

    def review_suggestions(self, text):
        """對使用者提供的段落/摘要給出審閱建議。"""
        if not text.strip():
            return "請提供要審閱的文字內容。"
        system = (
            "你是嚴謹的論文審閱人。請用繁體中文，針對以下文字給出結構化審閱意見："
            "## 優點、## 待改進（條列，聚焦論述清晰度、方法嚴謹性、實驗完整性）、"
            "## 具體修改建議（可操作）。務實直接，不要客套。"
        )
        try:
            return self._chat(system, f"=== 待審閱文字 ===\n{text}", max_tokens=1200)
        except Exception as e:
            self.logger.error(f"審閱建議失敗: {e}")
            return f"產生審閱建議時發生錯誤：{e}"

    def slides_outline(self, topic, papers=None):
        """產生簡報大綱（每張投影片標題 + 重點）。"""
        context = ""
        if papers:
            context = "\n".join(f"- {p['title']}" for p in papers)
        system = (
            "你是簡報設計助手。請用繁體中文，為指定主題產出 8-10 張投影片的大綱，"
            "每張用 `### 第N張：標題` 開頭，下面 2-4 個重點條列。"
            "涵蓋動機、背景、方法、比較、結論與未來方向。"
        )
        user = f"主題：{topic}"
        if context:
            user += f"\n\n可涵蓋的相關論文：\n{context}"
        try:
            return self._chat(system, user, temperature=0.5, max_tokens=1500)
        except Exception as e:
            self.logger.error(f"簡報大綱失敗: {e}")
            return f"產生簡報大綱時發生錯誤：{e}"
