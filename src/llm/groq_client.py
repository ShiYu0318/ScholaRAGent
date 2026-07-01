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
