"""SQLite 關聯式儲存層（標準庫，無外部依賴）。

保存清理後的論文資料與使用者互動事件，供互動追蹤（Week10）、
排序優化（Week14）與趨勢分析（Week13）使用。與 FAISS 向量庫平行：
向量庫負責語意檢索，SQLite 負責結構化查詢與統計。
"""
import sqlite3
import threading
from datetime import datetime, timezone

from src import config
from src.utils.logger import get_logger

_SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    id         TEXT PRIMARY KEY,
    title      TEXT NOT NULL,
    abstract   TEXT,
    authors    TEXT,
    link       TEXT,
    published  TEXT,
    summary    TEXT,
    source     TEXT DEFAULT 'arxiv',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS interactions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id   TEXT,
    user_id    TEXT,
    action     TEXT NOT NULL,
    value      REAL DEFAULT 1.0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (paper_id) REFERENCES papers(id)
);
CREATE INDEX IF NOT EXISTS idx_interactions_paper  ON interactions(paper_id);
CREATE INDEX IF NOT EXISTS idx_interactions_action ON interactions(action);
CREATE INDEX IF NOT EXISTS idx_papers_published    ON papers(published);
"""

def _now():
    return datetime.now(timezone.utc).isoformat()


class Database:
    """輕量 SQLite 封裝，執行緒安全（bot 於背景執行緒寫入）。"""

    def __init__(self, path=None):
        self.logger = get_logger(self.__class__.__name__)
        self.path = str(path or config.DB_PATH)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        self.logger.info(f"SQLite 就緒：{self.path}")

    # ---- 論文 ----
    def upsert_paper(self, paper):
        """新增或更新一篇論文（依 id）。回傳是否為新論文。"""
        with self._lock:
            existed = self._conn.execute(
                "SELECT 1 FROM papers WHERE id = ?", (paper["id"],)
            ).fetchone()
            self._conn.execute(
                """
                INSERT INTO papers (id, title, abstract, authors, link, published, summary, source, created_at)
                VALUES (:id, :title, :abstract, :authors, :link, :published, :summary, :source, :created_at)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title, abstract=excluded.abstract, authors=excluded.authors,
                    link=excluded.link, published=excluded.published,
                    summary=COALESCE(excluded.summary, papers.summary),
                    source=excluded.source
                """,
                {
                    "id": paper["id"],
                    "title": paper.get("title", ""),
                    "abstract": paper.get("abstract", ""),
                    "authors": paper.get("authors", ""),
                    "link": paper.get("link", ""),
                    "published": paper.get("published", ""),
                    "summary": paper.get("summary"),
                    "source": paper.get("source", "arxiv"),
                    "created_at": _now(),
                },
            )
            self._conn.commit()
            return existed is None

    def upsert_papers(self, papers):
        """批次寫入，回傳實際新增（先前不存在）的數量。"""
        return sum(1 for p in papers if self.upsert_paper(p))

    def get_paper(self, paper_id):
        row = self._conn.execute(
            "SELECT * FROM papers WHERE id = ?", (paper_id,)
        ).fetchone()
        return dict(row) if row else None

    def all_papers(self, limit=None, source=None):
        sql = "SELECT * FROM papers"
        params = []
        if source:
            sql += " WHERE source = ?"
            params.append(source)
        sql += " ORDER BY published DESC, created_at DESC"
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        return [dict(r) for r in self._conn.execute(sql, params).fetchall()]

    def count_papers(self):
        return self._conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]

    # ---- 互動 ----
    def log_interaction(self, action, paper_id=None, user_id=None, value=1.0):
        """記錄一筆使用者互動（click / like / subscribe / rate / ask / share…）。"""
        with self._lock:
            self._conn.execute(
                "INSERT INTO interactions (paper_id, user_id, action, value, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (paper_id, str(user_id) if user_id is not None else None, action, float(value), _now()),
            )
            self._conn.commit()

    def interaction_counts(self, action=None):
        """回傳 {paper_id: 加權互動總分}，可指定只計某類 action。"""
        sql = "SELECT paper_id, SUM(value) AS total FROM interactions WHERE paper_id IS NOT NULL"
        params = []
        if action:
            sql += " AND action = ?"
            params.append(action)
        sql += " GROUP BY paper_id"
        return {r["paper_id"]: r["total"] for r in self._conn.execute(sql, params).fetchall()}

    def action_totals(self):
        """回傳 {action: 次數}，供互動總覽。"""
        rows = self._conn.execute(
            "SELECT action, COUNT(*) AS n FROM interactions GROUP BY action"
        ).fetchall()
        return {r["action"]: r["n"] for r in rows}

    def close(self):
        self._conn.close()
