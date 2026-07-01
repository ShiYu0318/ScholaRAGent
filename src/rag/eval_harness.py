"""檢索評估 harness（E1）：把 A6 指標套用到黃金題組，做回歸驗證。

dataset：[{"query": str, "relevant": [id, ...]}, ...]
retrieve：retrieve(query, k) -> [(paper, score)]（paper 需有 "id"）。
回傳各指標的平均，任何 RAG 改動都能量化「有沒有變好」。
"""
from src.rag.evaluation import precision_at_k, recall, reciprocal_rank


def evaluate_retrieval(retrieve, dataset, k=5):
    if not dataset:
        return {"precision@k": 0.0, "recall": 0.0, "mrr": 0.0, "n": 0}

    p_sum = r_sum = rr_sum = 0.0
    for item in dataset:
        hits = retrieve(item["query"], k=k)
        ids = [p["id"] for p, _ in hits]
        relevant = set(item["relevant"])
        p_sum += precision_at_k(ids, relevant, k)
        r_sum += recall(ids, relevant)
        rr_sum += reciprocal_rank(ids, relevant)

    n = len(dataset)
    return {
        "precision@k": p_sum / n,
        "recall": r_sum / n,
        "mrr": rr_sum / n,
        "n": n,
    }
