"""RAGAS 式 LLM-judge 指標：離線（stub LLM 回固定 JSON）。"""
import pytest

from src.rag.llm_judge import (
    evaluate_answer,
    judge_answer_relevancy,
    judge_context_precision,
    judge_context_recall,
    judge_faithfulness,
)


class StubLLM:
    """依 system prompt 關鍵字回對應 JSON，記錄呼叫供斷言。"""

    def __init__(self, responses=None):
        self.responses = responses or {}
        self.calls = []

    def _chat(self, system, user, **kwargs):
        self.calls.append({"system": system, "user": user})
        for key, resp in self.responses.items():
            if key in system:
                return resp
        return "{}"


def test_faithfulness_counts_supported_claims():
    llm = StubLLM({"事實查核員": (
        '{"claims": [{"claim": "A", "supported": true},'
        ' {"claim": "B", "supported": true},'
        ' {"claim": "C", "supported": false}]}'
    )})
    out = judge_faithfulness(llm, "答案文字", ["ctx1", "ctx2"])
    assert out["score"] == pytest.approx(2 / 3)
    assert len(out["claims"]) == 3
    # 上下文有編號地送進 prompt
    assert "[1] ctx1" in llm.calls[0]["user"]


def test_faithfulness_empty_inputs():
    llm = StubLLM()
    assert judge_faithfulness(llm, "", ["ctx"])["score"] == 0.0
    assert judge_faithfulness(llm, "ans", [])["score"] == 0.0
    assert llm.calls == []  # 空輸入不浪費 judge 呼叫


def test_answer_relevancy_normalizes_to_unit():
    llm = StubLLM({"切題程度": '{"score": 7}'})
    assert judge_answer_relevancy(llm, "Q", "A")["score"] == pytest.approx(0.7)
    # 超界分數截斷
    llm2 = StubLLM({"切題程度": '{"score": 15}'})
    assert judge_answer_relevancy(llm2, "Q", "A")["score"] == 1.0


def test_context_precision_fraction():
    llm = StubLLM({"實質幫助": '{"relevant": [true, false, true, false]}'})
    out = judge_context_precision(llm, "Q", ["c1", "c2", "c3", "c4"])
    assert out["score"] == 0.5
    assert out["relevant"] == [True, False, True, False]


def test_context_recall_requires_ground_truth():
    llm = StubLLM({"標準答案": (
        '{"statements": [{"statement": "s1", "covered": true},'
        ' {"statement": "s2", "covered": false}]}'
    )})
    out = judge_context_recall(llm, "Q", "ground truth", ["ctx"])
    assert out["score"] == 0.5
    assert judge_context_recall(llm, "Q", "", ["ctx"])["score"] == 0.0


def test_evaluate_answer_aggregates_and_isolates_failures():
    llm = StubLLM({
        "事實查核員": '{"claims": [{"claim": "A", "supported": true}]}',
        "切題程度": "這不是 JSON",  # 單一指標壞掉
        "實質幫助": '{"relevant": [true]}',
        "標準答案": '{"statements": [{"statement": "s", "covered": true}]}',
    })
    out = evaluate_answer(llm, "Q", "A", ["ctx"], ground_truth="GT")
    assert out["faithfulness"] == 1.0
    assert out["context_precision"] == 1.0
    assert out["context_recall"] == 1.0
    assert out["answer_relevancy"] is None  # 失敗記 None 不炸整體
    assert "answer_relevancy" in out["errors"]


def test_evaluate_answer_skips_recall_without_ground_truth():
    llm = StubLLM({
        "事實查核員": '{"claims": []}',
        "切題程度": '{"score": 5}',
        "實質幫助": '{"relevant": []}',
    })
    out = evaluate_answer(llm, "Q", "A", ["ctx"])
    assert "context_recall" not in out
