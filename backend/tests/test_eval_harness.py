"""檢索評估 harness。"""
from src.rag.eval_harness import evaluate_retrieval


def _make_retrieve(data):
    def retrieve(query, k=4):
        return [({"id": i}, 1.0) for i in data.get(query, [])][:k]
    return retrieve


def test_aggregates_metrics_across_dataset():
    retrieve = _make_retrieve({"q1": ["a", "b"], "q2": ["x", "c"]})
    dataset = [{"query": "q1", "relevant": ["a"]},
               {"query": "q2", "relevant": ["c"]}]
    res = evaluate_retrieval(retrieve, dataset, k=2)
    # q1: 命中在第1名 -> RR 1.0；q2: c 在第2名 -> RR 0.5
    assert res["mrr"] == 0.75
    assert res["recall"] == 1.0
    assert res["precision@k"] == 0.5      # 每題 2 取 1 相關
    assert res["n"] == 2


def test_empty_dataset_returns_zeros():
    res = evaluate_retrieval(_make_retrieve({}), [], k=3)
    assert res["mrr"] == 0.0 and res["n"] == 0


class _JudgeStub:
    """固定回傳：faithfulness 1 claim supported、relevancy 8、precision [true]。"""

    def _chat(self, system, user, **kwargs):
        if "事實查核員" in system:
            return '{"claims": [{"claim": "A", "supported": true}]}'
        if "切題程度" in system:
            return '{"score": 8}'
        if "實質幫助" in system:
            return '{"relevant": [true, false]}'
        if "標準答案" in system:
            return '{"statements": [{"statement": "s", "covered": true}]}'
        return "{}"


def test_evaluate_answers_means_skip_none():
    from src.rag.eval_harness import evaluate_answers

    samples = [
        {"question": "q1", "answer": "a1", "contexts": ["c1", "c2"]},
        {"question": "q2", "answer": "a2", "contexts": ["c1", "c2"],
         "ground_truth": "gt"},
    ]
    res = evaluate_answers(_JudgeStub(), samples)
    assert res["n"] == 2
    assert res["means"]["faithfulness"] == 1.0
    assert res["means"]["answer_relevancy"] == 0.8
    assert res["means"]["context_precision"] == 0.5
    # 只有第二題有 ground_truth -> recall 平均只算一題
    assert res["means"]["context_recall"] == 1.0


def test_compare_pipelines_with_and_without_judge():
    from src.rag.eval_harness import compare_pipelines

    def good(query, k=5):
        return {"answer": "ans", "contexts": ["c"], "retrieved_ids": ["a", "b"]}

    def bad(query, k=5):
        return {"answer": "", "contexts": [], "retrieved_ids": ["x", "y"]}

    dataset = [{"query": "q", "relevant": ["a"], "ground_truth": "gt"}]
    report = compare_pipelines({"good": good, "bad": bad}, dataset, k=2)
    assert report["good"]["retrieval"]["mrr"] == 1.0
    assert report["bad"]["retrieval"]["mrr"] == 0.0
    assert report["good"]["judge"] is None  # 沒給 llm 就不跑 judge

    judged = compare_pipelines({"good": good}, dataset, k=2, llm=_JudgeStub())
    assert judged["good"]["judge"]["faithfulness"] == 1.0
