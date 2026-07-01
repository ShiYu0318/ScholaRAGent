"""RAG 離線評估指標（Advanced RAG / A6，RAGAS 精神的輕量版）。

不需外部服務即可回歸驗證檢索與生成品質：
- 檢索面：precision@k、recall、reciprocal rank（MRR 的單筆分量）。
- 生成面：faithfulness——答案內容詞有多少比例能在檢索脈絡中找到（幻覺代理指標）。

配合 `eval/` 黃金題組，任何 RAG 改動都能量化「有沒有變好」。
"""
import re

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(text):
    return set(_TOKEN.findall((text or "").lower()))


def precision_at_k(retrieved_ids, relevant_ids, k):
    """前 k 個檢索結果中，相關者的比例。"""
    top = retrieved_ids[:k]
    if not top:
        return 0.0
    hit = sum(1 for i in top if i in relevant_ids)
    return hit / len(top)


def recall(retrieved_ids, relevant_ids):
    """所有相關文件中，被檢索到的比例。"""
    if not relevant_ids:
        return 0.0
    hit = sum(1 for i in set(retrieved_ids) if i in relevant_ids)
    return hit / len(relevant_ids)


def reciprocal_rank(retrieved_ids, relevant_ids):
    """第一個相關結果名次的倒數；都沒命中回 0。"""
    for rank, i in enumerate(retrieved_ids, 1):
        if i in relevant_ids:
            return 1.0 / rank
    return 0.0


def faithfulness(answer, contexts):
    """答案內容詞有多少比例出現在檢索脈絡中（0~1，越高越可能有據）。"""
    ans = _tokens(answer)
    if not ans:
        return 0.0
    ctx = set()
    for c in contexts:
        ctx |= _tokens(c)
    return len(ans & ctx) / len(ans)


def citation_accuracy(answer, chunks):
    """片段級引用準確度（A8 [REF:id] 用），meetGRAG 精神。

    - valid_ratio：答案中的 [REF:id] 有多少比例對應到真實 chunk（來源/語法正確）。
    - grounded_ratio：有效引用中，被引 chunk 內容與答案有詞彙重疊的比例（有據）。
    - score：同時有效且有據的引用比例（越高越可信）。
    """
    from src.rag.chunk_citations import extract_refs

    refs = extract_refs(answer)
    if not refs:
        return {"score": 0.0, "valid_ratio": 0.0, "grounded_ratio": 0.0, "n_refs": 0}

    by_id = {c["id"]: c for c in chunks}
    ans_tokens = _tokens(answer)
    valid = [r for r in refs if r in by_id]
    grounded = [r for r in valid if _tokens(by_id[r].get("text", "")) & ans_tokens]

    return {
        "score": len(grounded) / len(refs),
        "valid_ratio": len(valid) / len(refs),
        "grounded_ratio": len(grounded) / len(valid) if valid else 0.0,
        "n_refs": len(refs),
    }
