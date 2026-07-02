"""產品層服務：趨勢、週報、使用者分析、學習路徑生成。

趨勢與分析為純統計（離線可測）；週報摘要與學習路徑生成會用 LLM，
失敗時降級為統計 / 檢索式結果，確保無金鑰也可用。
"""
import json
import re
import threading
from datetime import date, timedelta

from src.analysis.trends import extract_keywords, forecast, keyword_timeseries, trending_keywords
from src.recommend.ranker import rank_papers
from src.utils.logger import get_logger

_JSON_ARRAY = re.compile(r"\[.*\]", re.S)


class ProductService:
    def __init__(self, store, llm=None):
        self.logger = get_logger(self.__class__.__name__)
        self.store = store
        self._llm = llm

    @property
    def llm(self):
        if self._llm is None:
            from src.llm.groq_client import GroqClient
            self._llm = GroqClient()
        return self._llm

    # ---- 趨勢 ----
    def trends(self, granularity="month", top_n=10):
        papers = self.store.all_papers(limit=2000)
        rising = []
        for kw, slope in trending_keywords(papers, top_n=top_n, granularity=granularity):
            periods, counts = keyword_timeseries(papers, kw, granularity)
            rising.append({
                "keyword": kw,
                "slope": round(slope, 4),
                "periods": periods,
                "counts": counts,
                "forecast": round(forecast(counts), 2),
            })
        top = [{"keyword": kw, "count": c} for kw, c in extract_keywords(papers, top_n=top_n)]
        return {"rising": rising, "top": top, "total_papers": len(papers)}

    def keyword_series(self, keyword, granularity="month"):
        papers = self.store.all_papers(limit=2000)
        periods, counts = keyword_timeseries(papers, keyword, granularity)
        return {"keyword": keyword, "periods": periods, "counts": counts,
                "forecast": round(forecast(counts), 2)}

    # ---- 週報 ----
    def weekly_digest(self, user_id=None, top_n=8):
        since = (date.today() - timedelta(days=7)).isoformat()
        papers = self.store.all_papers(limit=2000)
        recent = [p for p in papers if (p.get("published") or "") >= since]
        window = "week"
        if not recent:
            # 一週內沒新論文時退回文庫最新的一批，避免空白週報
            recent = sorted(papers, key=lambda p: p.get("published") or "", reverse=True)[:20]
            window = "latest"
        ranked = rank_papers(recent, interaction_counts=self.store.interaction_counts())[:top_n]
        keywords = [{"keyword": kw, "count": c} for kw, c in extract_keywords(recent, top_n=8)]
        return {
            "since": since,
            "window": window,
            "total": len(recent),
            "papers": ranked,
            "keywords": keywords,
            "overview": self._overview(ranked),
        }

    def _overview(self, papers):
        if not papers:
            return None
        titles = "\n".join(f"- {p.get('title', '')}" for p in papers[:8])
        try:
            return self.llm._chat(
                "你是研究週報編輯。用繁體中文寫 2-3 句本週論文重點綜述，不要條列。",
                titles, max_tokens=300,
            )
        except Exception as e:
            self.logger.info(f"週報綜述生成失敗，僅回統計：{e}")
            return None

    # ---- 使用者分析 ----
    def analytics(self, user_id, days=14):
        totals = self.store.action_totals(user_id)
        reading = {"to-read": 0, "reading": 0, "done": 0}
        for it in self.store.reading_items(user_id):
            state = it.get("state")
            if state in reading:
                reading[state] += 1
        interactions = self.store.user_interactions(user_id, limit=500)
        cutoff = (date.today() - timedelta(days=days - 1)).isoformat()
        by_day = {}
        seen_papers = []
        for it in interactions:
            day = (it.get("created_at") or "")[:10]
            if day >= cutoff:
                by_day[day] = by_day.get(day, 0) + 1
            pid = it.get("paper_id")
            if pid and pid not in seen_papers:
                seen_papers.append(pid)
        interacted = [p for pid in seen_papers[:100]
                      if (p := self.store.get_paper(pid))]
        topics = [{"keyword": kw, "count": c}
                  for kw, c in extract_keywords(interacted, top_n=10)]
        activity = [{"date": d, "count": by_day[d]} for d in sorted(by_day)]
        return {
            "actions": totals,
            "reading": reading,
            "activity": activity,
            "topics": topics,
            "library": self.store.stats(),
        }

    # ---- 學習路徑 ----
    def generate_learning_path(self, user_id, topic, steps=6):
        titles = self._llm_steps(topic, steps) or self._fallback_steps(topic, steps)
        items = [{"title": t, "done": False} for t in titles]
        return self.store.create_learning_path(user_id, topic, items)

    def _llm_steps(self, topic, steps):
        try:
            raw = self.llm._chat(
                "你是研究學習規劃師。針對主題產出循序漸進的學習步驟，"
                f"只回傳 JSON 字串陣列（{steps} 項，每項一句繁體中文步驟），不要其他文字。",
                topic, max_tokens=600,
            )
            m = _JSON_ARRAY.search(raw or "")
            parsed = json.loads(m.group(0)) if m else []
            return [str(t).strip() for t in parsed if str(t).strip()][:steps] or None
        except Exception as e:
            self.logger.info(f"學習路徑 LLM 生成失敗，改用檢索式：{e}")
            return None

    def _fallback_steps(self, topic, steps):
        q = topic.lower()
        matched = [p for p in self.store.all_papers(limit=2000)
                   if q in (p.get("title") or "").lower()
                   or q in (p.get("abstract") or "").lower()]
        matched.sort(key=lambda p: p.get("published") or "")
        titles = [f"閱讀：{p['title']}" for p in matched[:steps - 1]]
        return [f"綜覽 {topic} 的核心概念與代表性方法", *titles][:steps]


_service = None
_service_lock = threading.Lock()


def get_product_service():
    global _service
    with _service_lock:
        if _service is None:
            from src.store import get_store
            _service = ProductService(get_store())
    return _service


def set_product_service(service):
    """測試注入；回傳先前實例。"""
    global _service
    prev, _service = _service, service
    return prev
