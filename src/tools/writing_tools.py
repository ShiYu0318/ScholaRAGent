"""寫作助理強化（Tools / D10）：升級 /latex 之外的論文寫作輔助。

- polish_text：文法／清晰度改寫（GEC）。
- extract_contributions：從草稿提煉貢獻點。
- review_checklist：投稿前的審稿式檢查清單。
皆為 LLM 編排，注入 stub 即可離線測試。
"""


def polish_text(text, llm):
    """語言潤飾：修正文法、提升學術清晰度，保留原意。"""
    system = (
        "你是學術英文編輯。修正文法、提升清晰度與學術語氣，保留原意，"
        "只輸出改寫後的文字。"
    )
    return llm._chat(system, text, max_tokens=700)


def extract_contributions(text, llm):
    """從草稿提煉條列式貢獻點（供 intro / abstract 使用）。"""
    system = "從以下內容提煉 3-5 點主要貢獻，條列輸出，動詞開頭、精煉。"
    return llm._chat(system, text, max_tokens=300)


def review_checklist(topic, llm):
    """產生投稿前的審稿式檢查清單。"""
    system = (
        "你是嚴謹的審稿人。針對這個主題的論文，列出投稿前應自我檢查的清單："
        "動機、相關工作、方法完整性、實驗充分性、可重現性、限制與倫理。條列。"
    )
    return llm._chat(system, f"主題：{topic}", max_tokens=500)
