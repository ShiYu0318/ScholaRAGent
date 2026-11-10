"""本地行事曆匯出：產生標準 iCalendar (.ics) 事件，免任何外部服務。

使用者可把產生的 .ics 匯入 Google Calendar / Apple 行事曆 / Outlook。
真正的 Google Calendar API（直接寫入雲端）需 OAuth 憑證，可日後接進同一工具介面。
"""
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

from src import config
from src.utils.logger import get_logger


def _fold(text):
    """iCalendar 需跳脫逗號/分號/換行。"""
    return (text or "").replace("\r\n", "\n").replace("\r", "\n").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME = re.compile(r"^\d{1,2}:\d{2}$")


def _validate(date, time):
    """date/time 來自 LLM 工具參數：會進檔名與 .ics 內容，必須嚴格比對格式。"""
    if not isinstance(date, str) or not _DATE.match(date):
        raise ValueError("日期格式需為 YYYY-MM-DD")
    datetime.strptime(date, "%Y-%m-%d")
    if time:
        if not isinstance(time, str) or not _TIME.match(time):
            raise ValueError("時間格式需為 HH:MM")
        hh, mm = (int(x) for x in time.split(":"))
        if hh > 23 or mm > 59:
            raise ValueError("時間超出範圍")


def build_ics(title, date, time=None, duration_hours=1, description=""):
    """組出單一 VEVENT 的 .ics 內容字串。

    - date：'YYYY-MM-DD'。
    - time：'HH:MM'，省略則為整日事件。
    """
    _validate(date, time)
    ymd = date.replace("-", "")
    uid = hashlib.sha1(f"{title}{date}{time}".encode("utf-8")).hexdigest()[:16] + "@scholaragent"
    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ScholaRAGent//Calendar//EN",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
    ]
    if time:
        hh, mm = time.split(":")
        start = f"{ymd}T{int(hh):02d}{int(mm):02d}00"
        end_hour = (int(hh) + int(duration_hours)) % 24
        lines.append(f"DTSTART:{start}")
        lines.append(f"DTEND:{ymd}T{end_hour:02d}{int(mm):02d}00")
    else:
        lines.append(f"DTSTART;VALUE=DATE:{ymd}")
    lines.append(f"SUMMARY:{_fold(title)}")
    if description:
        lines.append(f"DESCRIPTION:{_fold(description)}")
    lines += ["END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(lines) + "\r\n"


class CalendarExporter:
    def __init__(self, out_dir=None):
        self.logger = get_logger(self.__class__.__name__)
        self.out_dir = Path(out_dir or config.DATA_DIR)

    def save_event(self, title, date, time=None, duration_hours=1, description=""):
        """產生事件 .ics 並存檔，回傳給使用者的確認字串。"""
        try:
            ics = build_ics(title, date, time, duration_hours, description)
        except ValueError as e:
            return f"建立行事曆事件失敗：{e}"
        slug = hashlib.sha1(f"{title}{date}{time}".encode("utf-8")).hexdigest()[:8]
        name = f"event_{date}_{slug}.ics"
        try:
            self.out_dir.mkdir(parents=True, exist_ok=True)
            with open(self.out_dir / name, "w", encoding="utf-8") as f:
                f.write(ics)
        except Exception as e:
            self.logger.error(f"寫入 .ics 失敗：{e}")
            return "建立行事曆事件失敗"
        when = f"{date} {time}" if time else f"{date}（整日）"
        return f"已建立行事曆事件「{title}」於 {when}，檔名：{name}"
