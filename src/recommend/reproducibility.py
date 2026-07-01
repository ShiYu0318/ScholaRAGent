"""可重現性追蹤。

Papers-with-Code 已關站，改用最可靠的訊號：許多論文會在摘要／comment 寫出
程式碼倉庫連結（github/gitlab）。抽取這些連結，標記「有無官方實作」，
幫使用者快速判斷可否重現。純函式、離線可測；之後可再接 GitHub API 補 star 數。
"""
import re

# 允許 http(s)://、www.、或裸網域；抓 owner/repo
_REPO = re.compile(
    r"(?:https?://)?(?:www\.)?(?:github|gitlab)\.com/[\w.-]+/[\w.-]+",
    re.IGNORECASE,
)


def extract_code_links(paper):
    """從 title/abstract/comment 抽出唯一的 code 倉庫連結（正規化為 https）。"""
    text = " ".join(str(paper.get(f, "")) for f in ("title", "abstract", "comment"))
    links = []
    for m in _REPO.finditer(text):
        url = m.group(0).rstrip(".,);")
        if not url.lower().startswith("http"):
            url = "https://" + url.lstrip("/")
        url = url.replace("http://", "https://")
        if url not in links:
            links.append(url)
    return links


def reproducibility_signal(paper):
    """回傳 {has_code, repos}。"""
    repos = extract_code_links(paper)
    return {"has_code": bool(repos), "repos": repos}
