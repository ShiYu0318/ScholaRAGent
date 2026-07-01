"""本地行事曆匯出（Week12）：產生標準 iCalendar (.ics) 事件，免任何外部服務。

使用者可把產生的 .ics 匯入 Google Calendar / Apple 行事曆 / Outlook。
真正的 Google Calendar API（直接寫入雲端）需 OAuth 憑證，可日後接進同一工具介面。
"""
import hashlib
from datetime import datetime, timezone

from src import config
from src.utils.logger import get_logger


def _fold(text):
    """iCalendar 需跳脫逗號/分號/換行。"""
    return (text or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def build_ics(title, date, time=None, duration_hours=1, description=""):
    """組出單一 VEVENT 的 .ics 內容字串。

    - date：'YYYY-MM-DD'。
    - time：'HH:MM'，省略則為整日事件。
    """
    ymd = date.replace("-", "")
    uid = hashlib.sha1(f"{title}{date}{time}".encode("utf-8")).hexdigest()[:16] + "@air-agent"
    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AIR-Agent//Calendar//EN",
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
        self.out_dir = out_dir or config.DATA_DIR

    def save_event(self, title, date, time=None, duration_hours=1, description=""):
        """產生事件 .ics 並存檔，回傳給使用者的確認字串。"""
        ics = build_ics(title, date, time, duration_hours, description)
        slug = hashlib.sha1(f"{title}{date}{time}".encode("utf-8")).hexdigest()[:8]
        path = str(self.out_dir / f"event_{date}_{slug}.ics")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(ics)
        except Exception as e:
            self.logger.error(f"寫入 .ics 失敗：{e}")
            return f"建立行事曆事件失敗：{e}"
        when = f"{date} {time}" if time else f"{date}（整日）"
        return f"已建立行事曆事件「{title}」於 {when}，可匯入行事曆：{path}"
