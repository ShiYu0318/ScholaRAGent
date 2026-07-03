"""將長文切成有重疊的片段，供 RAG 收錄長篇報告 / 論文全文使用。

以「字元」為單位切分（中英混排時比以 token 切分更穩定），
並優先在段落 / 句子邊界斷開，避免把句子攔腰切斷。
"""
import re

_BOUNDARY = re.compile(r"(?<=[。！？.!?\n])")


def chunk_text(text, size=800, overlap=120):
    """把 text 切成長度約 size、相鄰片段重疊 overlap 字元的清單。

    - size：每段目標字元數。
    - overlap：相鄰片段重疊的字元數（保留上下文，改善檢索召回）。
    回傳去除前後空白後的非空片段清單；短文則原樣回傳單一片段。
    """
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    if overlap < 0:
        overlap = 0
    if overlap >= size:
        overlap = size // 4

    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        # 若還沒到結尾，往回找最近的句子 / 段落邊界，讓斷點更自然
        if end < n:
            window = text[start:end]
            boundaries = list(_BOUNDARY.finditer(window))
            if boundaries:
                last = boundaries[-1].end()
                # 邊界至少要落在後半段，避免片段太短
                if last >= size // 2:
                    end = start + last
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks
