"""跨 router 共用的輸入型別：長度/數量上限、JSON 大小、時區與時間格式。

原則：任何會被存下來或送進 LLM 的欄位都要有上限。
"""
import json
from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo, available_timezones

from pydantic import AfterValidator, Field

PaperId = Annotated[str, Field(min_length=1, max_length=200)]
ShortText = Annotated[str, Field(max_length=200)]
Tag = Annotated[str, Field(min_length=1, max_length=40)]


def _bounded_json(max_bytes):
    def check(value):
        if value is None:
            return value
        if len(json.dumps(value, ensure_ascii=False)) > max_bytes:
            raise ValueError(f"內容過大（上限 {max_bytes} bytes）")
        return value
    return check


def BoundedJson(max_bytes):  # noqa: N802 - 當型別工廠用
    return AfterValidator(_bounded_json(max_bytes))


def _timezone(value):
    if value is None:
        return value
    if value not in available_timezones():
        raise ValueError("未知的時區")
    ZoneInfo(value)
    return value


TimezoneName = Annotated[str, Field(max_length=64), AfterValidator(_timezone)]


def _iso_datetime(value):
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("需為 ISO 8601 時間，如 2026-07-03T09:00:00")
    return value


IsoDatetime = Annotated[str, Field(min_length=10, max_length=40), AfterValidator(_iso_datetime)]
