"""評估 harness：離線檢索指標 + RAGAS 式 judge 指標的批量與對照評估。

- evaluate_retrieval：檢索排序指標（precision@k / recall / MRR）回歸驗證。
- evaluate_answers：LLM-judge 指標批量跑 + 平均（llm_judge.evaluate_answer）。
- compare_pipelines：多個 RAG 管線在同一題組上的對照表（論文實驗用）。

dataset：[{"query": str, "relevant": [id, ...], "ground_truth"?: str}, ...]
retrieve：retrieve(query, k) -> [(paper, score)]（paper 需有 "id"）。
"""
from src.rag.evaluation import precision_at_k, recall, reciprocal_rank
from src.rag.llm_judge import evaluate_answer


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


def _means(items):
    """對 evaluate_answer 結果取每個指標的平均；None（judge 失敗）不計入。"""
    keys = {k for it in items for k in it if k != "errors"}
    means = {}
    for k in sorted(keys):
        vals = [it[k] for it in items if it.get(k) is not None]
        means[k] = sum(vals) / len(vals) if vals else None
    return means


def evaluate_answers(llm, samples):
    """批量跑 judge 指標。

    samples：[{"question", "answer", "contexts", "ground_truth"?}, ...]
    回傳 {"items": [各樣本 evaluate_answer 結果], "means": {指標: 平均}, "n"}。
    """
    items = [
        evaluate_answer(llm, s["question"], s.get("answer", ""),
                        s.get("contexts", []), ground_truth=s.get("ground_truth"))
        for s in samples
    ]
    return {"items": items, "means": _means(items), "n": len(items)}


def compare_pipelines(pipelines, dataset, k=5, llm=None):
    """對照多個 RAG 管線：檢索指標必跑；給 llm 才加跑 judge 指標。

    pipelines：{名稱: ask_fn}；ask_fn(question, k) 回傳
    {"answer": str, "contexts": [str], "retrieved_ids": [id]}。
    回傳 {名稱: {"retrieval": {...}, "judge": {...}|None}}。
    """
    report = {}
    for name, ask in pipelines.items():
        p_sum = r_sum = rr_sum = 0.0
        samples = []
        for item in dataset:
            out = ask(item["query"], k=k)
            ids = out.get("retrieved_ids", [])
            relevant = set(item["relevant"])
            p_sum += precision_at_k(ids, relevant, k)
            r_sum += recall(ids, relevant)
            rr_sum += reciprocal_rank(ids, relevant)
            samples.append({
                "question": item["query"],
                "answer": out.get("answer", ""),
                "contexts": out.get("contexts", []),
                "ground_truth": item.get("ground_truth"),
            })
        n = len(dataset) or 1
        report[name] = {
            "retrieval": {"precision@k": p_sum / n, "recall": r_sum / n,
                          "mrr": rr_sum / n, "n": len(dataset)},
            "judge": evaluate_answers(llm, samples)["means"] if llm else None,
        }
    return report
