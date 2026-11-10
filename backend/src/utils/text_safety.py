"""外部資料入庫/匯出前的文字清理。"""
from urllib.parse import urlsplit

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def safe_link(link) -> str:
    """只保留 http/https 連結；其他 scheme（javascript:、data: 等）一律清空。"""
    text = (link or "").strip()
    try:
        scheme = urlsplit(text).scheme.lower()
    except ValueError:
        return ""
    return text if scheme in ("http", "https") else ""


def csv_safe(value):
    """防 CSV 公式注入：以 = + - @ 開頭的儲存格前面加單引號，試算表會當成純文字。"""
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value
