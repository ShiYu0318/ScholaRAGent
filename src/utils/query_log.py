"""查詢可觀測性（E2）：把每次問答的查詢/命中/延遲寫成 JSONL，供 /stats 分析。"""
import json

from src.utils.logger import get_logger

_logger = get_logger("query_log")


def log_query(record, path):
    """附加一筆查詢紀錄（JSON 一行）。"""
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        _logger.error(f"寫入查詢日誌失敗：{e}")


def read_queries(path):
    """讀回所有查詢紀錄；檔案不存在回空清單。"""
    try:
        with open(path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []


def summarize(path):
    """彙總：總數、零命中數、平均延遲。"""
    rows = read_queries(path)
    if not rows:
        return {"total": 0, "zero_hit": 0, "avg_latency_ms": 0.0}
    total = len(rows)
    zero = sum(1 for r in rows if r.get("hits", 0) == 0)
    lat = [r.get("latency_ms", 0) for r in rows]
    return {
        "total": total,
        "zero_hit": zero,
        "avg_latency_ms": sum(lat) / total,
    }
