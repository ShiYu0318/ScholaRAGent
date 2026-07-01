"""calendar_ics：iCalendar 產生（整日 / 定時）、存檔、工具註冊。"""
from src.tools.calendar_ics import build_ics, CalendarExporter
from src.tools import builtins
from src import config


def test_build_ics_all_day():
    ics = build_ics("Paper deadline", "2026-07-10")
    assert "BEGIN:VCALENDAR" in ics and "END:VCALENDAR" in ics
    assert "BEGIN:VEVENT" in ics
    assert "SUMMARY:Paper deadline" in ics
    assert "DTSTART;VALUE=DATE:20260710" in ics


def test_build_ics_timed_event():
    ics = build_ics("Meeting", "2026-07-10", time="09:30", duration_hours=2)
    assert "DTSTART:20260710T093000" in ics
    assert "DTEND:20260710T113000" in ics  # +2 小時


def test_build_ics_escapes_special_chars():
    ics = build_ics("A, B; C", "2026-07-10", description="line1\nline2")
    assert "SUMMARY:A\\, B\\; C" in ics
    assert "DESCRIPTION:line1\\nline2" in ics


def test_save_event_writes_file(tmp_path):
    exp = CalendarExporter(out_dir=tmp_path)
    msg = exp.save_event("Demo", "2026-07-10", time="14:00")
    assert "已建立行事曆事件" in msg
    files = list(tmp_path.glob("*.ics"))
    assert len(files) == 1
    assert "BEGIN:VEVENT" in files[0].read_text(encoding="utf-8")


def test_calendar_tool_registered(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TASKS_PATH", tmp_path / "tasks.json")
    reg = builtins.build_default_registry(calendar=CalendarExporter(out_dir=tmp_path))
    assert "add_calendar_event" in reg.names()
    out = reg.execute("add_calendar_event", {"title": "Review", "date": "2026-07-11"})
    assert "已建立行事曆事件" in out
