"""每人通知排程器：依 notification_preferences 排每日/每週摘要，並輪詢到期提醒。

APScheduler BackgroundScheduler；broadcast 可注入替身供離線測試。
「web」頻道的摘要直接顯示於儀表板（Home 週報卡），不經 broadcast；
telegram/email/line 頻道透過 notify.dispatcher 推送（未設金鑰自動略過）。
"""
import threading
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.utils.logger import get_logger

_PUSH_CHANNELS = {"telegram", "email", "line"}


class SchedulerManager:
    def __init__(self, store=None, broadcast=None):
        self.logger = get_logger(self.__class__.__name__)
        self._store = store
        self._broadcast = broadcast
        self._scheduler = None
        self._notified = set()   # 已推播的 reminder id（行程內去重）
        self._sent = {}          # user_id -> 已推過的 paper id（dedupe 偏好用）

    @property
    def store(self):
        if self._store is None:
            from src.store import get_store
            self._store = get_store()
        return self._store

    def _push(self, text, channels):
        """把 text 送到使用者指定且全域已啟用的推送頻道。"""
        if self._broadcast is not None:
            return self._broadcast(text, channels)
        wanted = set(channels) & _PUSH_CHANNELS
        if not wanted:
            return {}
        from src.notify.dispatcher import broadcast, enabled_notifiers
        notifiers = [n for n in enabled_notifiers() if n.name in wanted]
        return broadcast(text, notifiers=notifiers)

    # ---- 生命週期 ----
    def start(self):
        if self._scheduler is not None:
            return
        self._scheduler = BackgroundScheduler(timezone="UTC")
        self._scheduler.add_job(self.tick_reminders, "interval",
                                minutes=1, id="reminders")
        self.schedule_all()
        self._scheduler.start()
        self.logger.info("排程器啟動")

    def stop(self):
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None

    def status(self):
        if self._scheduler is None:
            return {"running": False, "jobs": []}
        jobs = [{"id": j.id,
                 "next_run": j.next_run_time.isoformat() if j.next_run_time else None}
                for j in self._scheduler.get_jobs()]
        return {"running": self._scheduler.running, "jobs": jobs}

    # ---- 每人摘要排程 ----
    def schedule_all(self):
        for user in self.store.all_users():
            self.schedule_user(user["id"])

    def schedule_user(self, user_id):
        """依偏好（重新）建立該使用者的摘要任務；frequency=off 則移除。"""
        if self._scheduler is None:
            return
        job_id = f"digest:{user_id}"
        prefs = self.store.get_notification_prefs(user_id)
        if prefs.get("frequency") == "off":
            if self._scheduler.get_job(job_id):
                self._scheduler.remove_job(job_id)
            return
        kwargs = {"hour": prefs["hour"], "minute": prefs["minute"],
                  "timezone": prefs.get("timezone") or "UTC"}
        if prefs.get("frequency") == "weekly":
            kwargs["day_of_week"] = "mon"
        try:
            trigger = CronTrigger(**kwargs)
        except Exception as e:
            self.logger.warning(f"使用者 {user_id} 偏好無效，略過排程：{e}")
            return
        self._scheduler.add_job(self.send_digest, trigger, args=[user_id],
                                id=job_id, replace_existing=True)

    def send_digest(self, user_id):
        prefs = self.store.get_notification_prefs(user_id)
        if self._in_quiet(prefs):
            return None
        from src.api.services.library import get_library_service
        papers = get_library_service().personalized(user_id, top_n=5)
        if prefs.get("dedupe", True):
            sent = self._sent.setdefault(user_id, set())
            papers = [p for p in papers if p.get("id") not in sent]
            sent.update(p.get("id") for p in papers)
        if not papers:
            return None
        lines = [f"- {p.get('title', '')}\n  {p.get('link', '')}" for p in papers]
        text = "RAGency 個人化摘要\n" + "\n".join(lines)
        return self._push(text, prefs.get("channels") or [])

    def _in_quiet(self, prefs, now=None):
        start, end = prefs.get("quiet_start"), prefs.get("quiet_end")
        if start is None or end is None:
            return False
        hour = (now or datetime.now()).hour
        if start <= end:
            return start <= hour < end
        return hour >= start or hour < end  # 跨午夜區間，如 22-7

    # ---- 提醒 ----
    def tick_reminders(self, now_iso=None):
        now_iso = now_iso or datetime.now().isoformat(timespec="seconds")
        fired = []
        for r in self.store.due_reminders(now_iso):
            if r["id"] in self._notified:
                continue
            self._notified.add(r["id"])
            prefs = self.store.get_notification_prefs(r["user_id"])
            self._push(f"提醒：{r['text']}", prefs.get("channels") or [])
            fired.append(r["id"])
        return fired


_manager = None
_manager_lock = threading.Lock()


def get_scheduler_manager():
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = SchedulerManager()
    return _manager


def set_scheduler_manager(manager):
    """測試注入；回傳先前實例。"""
    global _manager
    prev, _manager = _manager, manager
    return prev
