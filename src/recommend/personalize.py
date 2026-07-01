"""每日個人化過濾（Recommend / D11）。

arXiv 每日論文是 firehose——用「使用者興趣輪廓」（過往查詢／按讚論文的文字）
建一個興趣向量，對當日候選論文依語意相似度排序，只推最可能在意的前 N 篇。
無輪廓時原樣回傳前 N 篇（不做假設）。與 [reward] 偏好模型互補。
"""
import numpy as np

from src.utils.logger import get_logger

_logger = get_logger("personalize")


def personalize_daily(papers, profile_texts, embedder, top_n=5):
    """依興趣輪廓相似度排序 papers，回傳前 top_n。"""
    if not papers:
        return []
    if not profile_texts:
        return papers[:top_n]

    profile = embedder.encode(profile_texts)
    profile_vec = np.asarray(profile).mean(axis=0)
    norm = np.linalg.norm(profile_vec)
    if norm > 0:
        profile_vec = profile_vec / norm

    docs = [f"{p.get('title', '')}. {p.get('abstract', '')}" for p in papers]
    doc_vecs = embedder.encode(docs)
    scores = np.asarray(doc_vecs) @ profile_vec

    order = np.argsort(scores)[::-1]
    return [papers[i] for i in order[:top_n]]
