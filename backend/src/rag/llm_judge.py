"""RAGAS 式 LLM-as-judge 評估指標：faithfulness、answer relevancy、
context precision、context recall。

刻意不依賴 ragas 套件（它會拉進整個 langchain 生態系與版本衝突）；
用專案既有的 GroqClient（只需 `_chat(system, user)` 介面，替身極易注入）
實作同概念指標。所有分數皆為 0-1；judge 輸出用 0-10 整數再正規化，
比要求 LLM 直接給小數穩定。
"""
import json
import re

_JSON_OBJ = re.compile(r"\{.*\}", re.S)


def _parse_json(raw):
    m = _JSON_OBJ.search(raw or "")
    if not m:
        raise ValueError(f"judge 回應不含 JSON：{raw!r}")
    return json.loads(m.group(0))


def _join_contexts(contexts):
    return "\n\n".join(f"[{i + 1}] {c}" for i, c in enumerate(contexts))


def judge_faithfulness(llm, answer, contexts):
    """答案忠實度：把答案拆成主張，逐一判斷能否由上下文直接支持。

    回傳 {"score": supported/total, "claims": [{"claim", "supported"}]}。
    """
    if not answer or not contexts:
        return {"score": 0.0, "claims": []}
    raw = llm._chat(
        "你是嚴格的事實查核員。把「答案」拆成獨立的事實主張，逐一判斷該主張"
        "是否能由「上下文」直接支持（不得靠常識腦補）。只回傳 JSON："
        '{"claims": [{"claim": "主張內容", "supported": true|false}, ...]}',
        f"上下文：\n{_join_contexts(contexts)}\n\n答案：\n{answer}",
        max_tokens=1000,
    )
    claims = _parse_json(raw).get("claims", [])
    if not claims:
        return {"score": 0.0, "claims": []}
    supported = sum(1 for c in claims if c.get("supported"))
    return {"score": supported / len(claims), "claims": claims}


def judge_answer_relevancy(llm, question, answer):
    """答案切題度：答案是否直接、完整回應了問題（不評對錯，只評切題）。"""
    if not answer:
        return {"score": 0.0}
    raw = llm._chat(
        "評估「答案」對「問題」的切題程度：是否直接回應問題、不答非所問、"
        "不塞無關內容。不評判事實正確性。只回傳 JSON："
        '{"score": 0到10的整數}',
        f"問題：{question}\n\n答案：\n{answer}",
        max_tokens=200,
    )
    score = _parse_json(raw).get("score", 0)
    return {"score": max(0.0, min(10, int(score))) / 10}


def judge_context_precision(llm, question, contexts):
    """上下文精確率：檢回的每段上下文對回答該問題是否真的有用。"""
    if not contexts:
        return {"score": 0.0, "relevant": []}
    raw = llm._chat(
        "逐段判斷每個「上下文」段落對回答「問題」是否有實質幫助。"
        "只回傳 JSON，陣列長度須等於段落數："
        '{"relevant": [true|false, ...]}',
        f"問題：{question}\n\n{_join_contexts(contexts)}",
        max_tokens=400,
    )
    flags = [bool(f) for f in _parse_json(raw).get("relevant", [])][: len(contexts)]
    if not flags:
        return {"score": 0.0, "relevant": []}
    return {"score": sum(flags) / len(flags), "relevant": flags}


def judge_context_recall(llm, question, ground_truth, contexts):
    """上下文召回率：標準答案的資訊點有多少能在檢回的上下文中找到。"""
    if not ground_truth or not contexts:
        return {"score": 0.0, "statements": []}
    raw = llm._chat(
        "把「標準答案」拆成獨立資訊點，逐一判斷該資訊點是否能在「上下文」"
        "中找到依據。只回傳 JSON："
        '{"statements": [{"statement": "資訊點", "covered": true|false}, ...]}',
        f"問題：{question}\n\n標準答案：\n{ground_truth}\n\n"
        f"上下文：\n{_join_contexts(contexts)}",
        max_tokens=1000,
    )
    stmts = _parse_json(raw).get("statements", [])
    if not stmts:
        return {"score": 0.0, "statements": []}
    covered = sum(1 for s in stmts if s.get("covered"))
    return {"score": covered / len(stmts), "statements": stmts}


def evaluate_answer(llm, question, answer, contexts, ground_truth=None):
    """跑全部 judge 指標；單一指標失敗（JSON 壞掉等）記 None，不炸整體。

    回傳 {"faithfulness", "answer_relevancy", "context_precision",
    "context_recall"(有 ground_truth 才有), "errors": {...}}。
    """
    metrics = {
        "faithfulness": lambda: judge_faithfulness(llm, answer, contexts),
        "answer_relevancy": lambda: judge_answer_relevancy(llm, question, answer),
        "context_precision": lambda: judge_context_precision(llm, question, contexts),
    }
    if ground_truth:
        metrics["context_recall"] = lambda: judge_context_recall(
            llm, question, ground_truth, contexts)

    result, errors = {}, {}
    for name, fn in metrics.items():
        try:
            result[name] = fn()["score"]
        except Exception as e:
            result[name] = None
            errors[name] = str(e)
    if errors:
        result["errors"] = errors
    return result
