"""查詢轉換（Advanced RAG / A2）：提升召回與精準度的前處理。

- HyDE：先讓 LLM 生成一段「假設性答案/論文片段」，用它去嵌入檢索，
  比原始問題更貼近文件語意空間。
- Multi-query：產生多個改寫版本，分別檢索後合併，涵蓋不同措辭。
- Decompose：把複雜問題拆成子問題，支援多跳檢索。

依賴一個具 `_chat(system, user)` 的 LLM 用戶端（即 GroqClient），方便離線用 stub 測試。
"""
import re

from src.utils.logger import get_logger

_NUM_PREFIX = re.compile(r"^\s*(?:\d+[.)、]|[-*•])\s*")


def _parse_lines(text, limit=None):
    """把 LLM 的多行輸出整理成清單（去除編號/項目符號與空行）。"""
    lines = []
    for raw in (text or "").splitlines():
        line = _NUM_PREFIX.sub("", raw).strip()
        if line:
            lines.append(line)
    return lines[:limit] if limit else lines


class QueryTransformer:
    def __init__(self, llm):
        self.logger = get_logger(self.__class__.__name__)
        self.llm = llm

    def hyde(self, query):
        """產生假設性文件片段（供嵌入檢索）。失敗時回退原查詢。"""
        system = (
            "你是 AI 研究助理。針對使用者的問題，寫一段 3-4 句、像出自論文摘要的"
            "假設性回答內容（可包含可能的方法名詞），用於語意檢索。只輸出該段文字。"
        )
        try:
            out = self.llm._chat(system, query, max_tokens=200)
            return out.strip() or query
        except Exception as e:
            self.logger.error(f"HyDE 失敗，改用原查詢：{e}")
            return query

    def multi_query(self, query, n=3):
        """回傳 [原查詢] + 最多 n 個改寫版本（去重）。"""
        system = (
            f"請把以下研究問題改寫成 {n} 個語意相同但用詞/角度不同的檢索查詢，"
            "每行一個，不要編號、不要多餘說明。"
        )
        variants = [query]
        try:
            out = self.llm._chat(system, query, max_tokens=200)
            for v in _parse_lines(out, limit=n):
                if v.lower() != query.lower() and v not in variants:
                    variants.append(v)
        except Exception as e:
            self.logger.error(f"multi-query 失敗：{e}")
        return variants

    def decompose(self, query, max_sub=4):
        """把複雜問題拆成子問題；若判定為單一問題則回傳 [原查詢]。"""
        system = (
            "若以下問題包含多個層面，請拆成數個可獨立檢索的子問題（每行一個、不要編號）；"
            "若本來就是單一問題，只輸出原問題。最多不超過 "
            f"{max_sub} 個。"
        )
        try:
            out = self.llm._chat(system, query, max_tokens=250)
            subs = _parse_lines(out, limit=max_sub)
            return subs or [query]
        except Exception as e:
            self.logger.error(f"decompose 失敗：{e}")
            return [query]
