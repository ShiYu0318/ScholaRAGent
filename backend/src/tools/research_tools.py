"""研究工作流工具：直擊研究生／研究員痛點。

- to_bibtex：一鍵匯出 BibTeX（引用管理煩）。
- literature_review：文獻綜述草稿 + 研究缺口（related work 難寫）。
- comparison_table：方法×資料集×指標比較表（追 SOTA 累）。
- explain_paper：逐節深讀導覽、名詞白話化（讀不懂密集論文）。

BibTeX 為純函式（好測）；其餘為 LLM 編排，注入 stub 即可離線測試。
"""
import re

from src.utils.logger import get_logger

_logger = get_logger("research_tools")
_WORD = re.compile(r"[A-Za-z0-9]+")


def _citation_key(paper):
    """產生 bibtex key：第一作者姓 + 年份 + 標題首字（小寫）。"""
    authors = paper.get("authors", "") or ""
    first = _WORD.findall(authors)
    surname = first[0].lower() if first else "anon"
    year = (paper.get("published", "") or "")[:4] or "n.d."
    title_words = _WORD.findall(paper.get("title", "") or "")
    # 跳過常見虛詞取第一個實詞
    stop = {"a", "an", "the", "is", "of", "on", "for", "to", "in"}
    tw = next((w.lower() for w in title_words if w.lower() not in stop), "")
    return f"{surname}{year}{tw}"


_BIBTEX_SPECIALS = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_"}


def _bibtex_text(value):
    """跳脫 BibTeX/LaTeX 特殊字元；大括號會破壞欄位結構，直接移除。"""
    text = str(value or "").replace("{", "").replace("}", "").replace("\\", "")
    return "".join(_BIBTEX_SPECIALS.get(ch, ch) for ch in text)


def _bibtex_authors(authors):
    """文庫以逗號分隔作者；BibTeX 要用 and，否則整串會被當成一個人。"""
    names = [a.strip() for a in (authors or "").split(",") if a.strip()]
    return " and ".join(_bibtex_text(n) for n in names)


def _suffix(n):
    """0 -> ''、1 -> 'a'、2 -> 'b' …（超過 26 個後接數字）。"""
    if n == 0:
        return ""
    return chr(ord("a") + n - 1) if n <= 26 else f"-{n}"


def to_bibtex(papers):
    """把論文清單轉成 BibTeX。空清單回空字串。

    - citation key 重複時依序加 a/b/c 後綴（重複的 key 會讓 LaTeX 編譯失敗）；
    - arXiv 論文輸出 eprint + archivePrefix，DOI 論文輸出 doi。
    """
    entries, used = [], {}
    for p in papers:
        base = _citation_key(p)
        count = used.get(base, 0)
        used[base] = count + 1
        key = base + _suffix(count)

        pid = str(p.get("id", "") or "")
        fields = [
            ("title", _bibtex_text(p.get("title", ""))),
            ("author", _bibtex_authors(p.get("authors", ""))),
            ("year", (p.get("published", "") or "")[:4]),
        ]
        if pid.startswith("doi:"):
            fields.append(("doi", pid[4:]))
        elif pid and (p.get("source") or "arxiv") == "arxiv":
            fields += [("eprint", pid), ("archivePrefix", "arXiv")]
        fields.append(("url", p.get("link", "")))
        body = ",\n".join(f"  {k} = {{{v}}}" for k, v in fields if v)
        entries.append(f"@misc{{{key},\n{body}\n}}")
    return "\n\n".join(entries)


def _papers_block(papers):
    return "\n".join(
        f"- {p.get('title', '')} — {p.get('abstract', '')[:300]}" for p in papers
    )


def literature_review(topic, papers, llm):
    """產生結構化文獻綜述草稿（含研究缺口）。"""
    system = (
        "你是資深研究者。根據提供的論文，撰寫一段結構化的文獻綜述："
        "分主題群組、比較方法、指出共識與研究缺口。繁體中文、條理清楚。"
    )
    user = f"主題：{topic}\n\n論文：\n{_papers_block(papers)}"
    return llm._chat(system, user, max_tokens=900)


def comparison_table(topic, papers, llm):
    """產生方法×資料集×指標的 Markdown 比較表。"""
    system = (
        "你會看到多篇論文。請抽取每篇的（方法、資料集、主要指標、關鍵結果），"
        "輸出一個 Markdown 表格。無法確定的欄位填 '—'。只輸出表格。"
    )
    user = f"主題：{topic}\n\n論文：\n{_papers_block(papers)}"
    return llm._chat(system, user, max_tokens=800)


def explain_paper(paper, llm):
    """逐節深讀導覽：白話講解、名詞解釋、公式直覺。"""
    system = (
        "你是耐心的研究導師。針對這篇論文，用繁體中文做深讀導覽："
        "研究問題、方法直覺、關鍵名詞白話化、貢獻與限制。分段清楚。"
    )
    user = f"標題：{paper.get('title', '')}\n摘要：{paper.get('abstract', '')}"
    return llm._chat(system, user, max_tokens=900)
