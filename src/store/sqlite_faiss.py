"""本機儲存後端：SQLite（關聯資料）+ FAISS（向量檢索）。

單一連線 + 執行緒鎖 + WAL，供 API 多執行緒使用。papers / interactions
schema 與 `db.Database` 一致（同一個檔案，bot 舊入口不受影響），
向量部分重用 `rag.VectorStore`（延遲初始化，embedder 可注入以利離線測試）。
"""
import json
import secrets
import sqlite3
import threading
from datetime import datetime, timezone

from src import config
from src.store.base import Store
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

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    google_sub    TEXT,
    github_id     TEXT,
    discord_id    TEXT,
    display_name  TEXT,
    locale        TEXT DEFAULT 'en',
    created_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS feeds (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    url        TEXT NOT NULL,
    title      TEXT,
    category   TEXT,
    enabled    INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    UNIQUE (user_id, url)
);
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    name       TEXT NOT NULL,
    keywords   TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (user_id, name)
);
CREATE TABLE IF NOT EXISTS conversations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    title       TEXT DEFAULT '',
    share_token TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    citations       TEXT,
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
CREATE TABLE IF NOT EXISTS reading_list (
    user_id    INTEGER NOT NULL,
    paper_id   TEXT NOT NULL,
    title      TEXT,
    state      TEXT DEFAULT 'to-read',
    tags       TEXT,
    note       TEXT DEFAULT '',
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, paper_id)
);
CREATE TABLE IF NOT EXISTS notification_preferences (
    user_id     INTEGER PRIMARY KEY,
    frequency   TEXT DEFAULT 'daily',
    hour        INTEGER DEFAULT 9,
    minute      INTEGER DEFAULT 0,
    timezone    TEXT DEFAULT 'Asia/Taipei',
    quiet_start INTEGER,
    quiet_end   INTEGER,
    min_score   REAL DEFAULT 0.0,
    dedupe      INTEGER DEFAULT 1,
    channels    TEXT
);
CREATE TABLE IF NOT EXISTS reminders (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    text       TEXT NOT NULL,
    due_at     TEXT NOT NULL,
    context    TEXT,
    done       INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS learning_paths (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    topic      TEXT NOT NULL,
    items      TEXT NOT NULL,
    progress   TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS user_skills (
    user_id    INTEGER NOT NULL,
    skill      TEXT NOT NULL,
    level      REAL DEFAULT 0,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, skill)
);
"""

_USER_OAUTH_FIELDS = ("google_sub", "github_id", "discord_id")
_READING_STATES = ("to-read", "reading", "done")
_PREF_DEFAULTS = {
    "frequency": "daily", "hour": 9, "minute": 0, "timezone": "Asia/Taipei",
    "quiet_start": None, "quiet_end": None, "min_score": 0.0,
    "dedupe": True, "channels": ["web"],
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _loads(text, default):
    if not text:
        return default
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return default


class SqliteFaissStore(Store):
    def __init__(self, db_path=None, embedder=None, vector_store=None):
        self.logger = get_logger(self.__class__.__name__)
        self.path = str(db_path or config.DB_PATH)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA busy_timeout = 5000")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        self._embedder = embedder
        self._vs = vector_store
        self.logger.info(f"SQLite+FAISS store 就緒：{self.path}")

    # 向量庫延遲初始化：載 embedding 模型很重，只有用到檢索才建
    @property
    def vector(self):
        if self._vs is None:
            from src.rag.vector_store import VectorStore
            self._vs = VectorStore(embedder=self._embedder)
        return self._vs

    def _write(self, sql, params=()):
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    # ---- 使用者 ----
    def create_user(self, email, password_hash=None, display_name=None,
                    locale="en", google_sub=None, github_id=None, discord_id=None):
        email = email.strip().lower()
        try:
            cur = self._write(
                "INSERT INTO users (email, password_hash, google_sub, github_id, discord_id,"
                " display_name, locale, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (email, password_hash, google_sub, github_id, discord_id,
                 display_name or email.split("@")[0], locale, _now()),
            )
        except sqlite3.IntegrityError:
            raise ValueError(f"email 已註冊：{email}")
        return self.get_user(cur.lastrowid)

    def get_user(self, user_id):
        row = self._conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

    def get_user_by_email(self, email):
        row = self._conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
        return dict(row) if row else None

    def get_user_by_oauth(self, field, value):
        if field not in _USER_OAUTH_FIELDS:
            raise ValueError(f"未知 OAuth 欄位：{field}")
        row = self._conn.execute(
            f"SELECT * FROM users WHERE {field} = ?", (str(value),)
        ).fetchone()
        return dict(row) if row else None

    def update_user(self, user_id, **fields):
        allowed = {"password_hash", "display_name", "locale", *_USER_OAUTH_FIELDS}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if updates:
            sets = ", ".join(f"{k} = ?" for k in updates)
            self._write(f"UPDATE users SET {sets} WHERE id = ?", (*updates.values(), user_id))
        return self.get_user(user_id)

    # ---- 論文 / 互動 ----
    def upsert_papers(self, papers):
        added = 0
        for p in papers:
            with self._lock:
                existed = self._conn.execute(
                    "SELECT 1 FROM papers WHERE id = ?", (p["id"],)
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
                        "id": p["id"], "title": p.get("title", ""), "abstract": p.get("abstract", ""),
                        "authors": p.get("authors", ""), "link": p.get("link", ""),
                        "published": p.get("published", ""), "summary": p.get("summary"),
                        "source": p.get("source", "arxiv"), "created_at": _now(),
                    },
                )
                self._conn.commit()
            added += existed is None
        return added

    def get_paper(self, paper_id):
        row = self._conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
        return dict(row) if row else None

    def all_papers(self, limit=None, source=None):
        sql, params = "SELECT * FROM papers", []
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

    def log_interaction(self, action, paper_id=None, user_id=None, value=1.0):
        self._write(
            "INSERT INTO interactions (paper_id, user_id, action, value, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (paper_id, str(user_id) if user_id is not None else None, action, float(value), _now()),
        )

    def interaction_counts(self, action=None):
        sql = ("SELECT paper_id, SUM(value) AS total FROM interactions"
               " WHERE paper_id IS NOT NULL")
        params = []
        if action:
            sql += " AND action = ?"
            params.append(action)
        sql += " GROUP BY paper_id"
        return {r["paper_id"]: r["total"] for r in self._conn.execute(sql, params).fetchall()}

    def action_totals(self, user_id=None):
        sql, params = "SELECT action, COUNT(*) AS n FROM interactions", []
        if user_id is not None:
            sql += " WHERE user_id = ?"
            params.append(str(user_id))
        sql += " GROUP BY action"
        return {r["action"]: r["n"] for r in self._conn.execute(sql, params).fetchall()}

    def user_interactions(self, user_id, limit=200):
        rows = self._conn.execute(
            "SELECT * FROM interactions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (str(user_id), limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # ---- 向量檢索 ----
    def index_papers(self, papers):
        return self.vector.add(papers)

    def search_scored(self, query, k=4, where=None, rerank=True):
        return self.vector.search_scored(query, k=k, where=where, rerank=rerank)

    # ---- RSS feeds ----
    def add_feed(self, user_id, url, title=None, category=None):
        try:
            cur = self._write(
                "INSERT INTO feeds (user_id, url, title, category, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, url.strip(), title, category, _now()),
            )
        except sqlite3.IntegrityError:
            raise ValueError(f"已訂閱過此來源:{url}")
        return self._feed(cur.lastrowid)

    def _feed(self, feed_id):
        row = self._conn.execute("SELECT * FROM feeds WHERE id = ?", (feed_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["enabled"] = bool(d["enabled"])
        return d

    def list_feeds(self, user_id):
        rows = self._conn.execute(
            "SELECT * FROM feeds WHERE user_id = ? ORDER BY created_at", (user_id,)
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["enabled"] = bool(d["enabled"])
            out.append(d)
        return out

    def update_feed(self, feed_id, user_id, **fields):
        allowed = {"url", "title", "category", "enabled"}
        updates = {k: (int(v) if k == "enabled" else v) for k, v in fields.items() if k in allowed}
        if updates:
            sets = ", ".join(f"{k} = ?" for k in updates)
            cur = self._write(
                f"UPDATE feeds SET {sets} WHERE id = ? AND user_id = ?",
                (*updates.values(), feed_id, user_id),
            )
            if cur.rowcount == 0:
                return None
        return self._feed(feed_id)

    def delete_feed(self, feed_id, user_id):
        cur = self._write("DELETE FROM feeds WHERE id = ? AND user_id = ?", (feed_id, user_id))
        return cur.rowcount > 0

    # ---- 主題訂閱 ----
    def add_subscription(self, user_id, name, keywords):
        kws = json.dumps([k.lower() for k in keywords], ensure_ascii=False)
        self._write(
            "INSERT INTO user_subscriptions (user_id, name, keywords, created_at) VALUES (?, ?, ?, ?)"
            " ON CONFLICT(user_id, name) DO UPDATE SET keywords=excluded.keywords",
            (user_id, name, kws, _now()),
        )
        return {"name": name, "keywords": _loads(kws, [])}

    def list_subscriptions(self, user_id):
        rows = self._conn.execute(
            "SELECT name, keywords FROM user_subscriptions WHERE user_id = ? ORDER BY created_at",
            (user_id,),
        ).fetchall()
        return [{"name": r["name"], "keywords": _loads(r["keywords"], [])} for r in rows]

    def remove_subscription(self, user_id, name):
        cur = self._write(
            "DELETE FROM user_subscriptions WHERE user_id = ? AND name = ?", (user_id, name)
        )
        return cur.rowcount > 0

    # ---- 對話 ----
    def create_conversation(self, user_id, title=""):
        now = _now()
        cur = self._write(
            "INSERT INTO conversations (user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (user_id, title, now, now),
        )
        return self._conversation_row(cur.lastrowid)

    def _conversation_row(self, conv_id):
        row = self._conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conv_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_conversations(self, user_id, query=None, limit=50):
        if query:
            like = f"%{query}%"
            rows = self._conn.execute(
                """
                SELECT DISTINCT c.* FROM conversations c
                LEFT JOIN messages m ON m.conversation_id = c.id
                WHERE c.user_id = ? AND (c.title LIKE ? OR m.content LIKE ?)
                ORDER BY c.updated_at DESC LIMIT ?
                """,
                (user_id, like, like, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_conversation(self, conv_id, user_id=None):
        conv = self._conversation_row(conv_id)
        if not conv or (user_id is not None and conv["user_id"] != user_id):
            return None
        conv["messages"] = self._messages(conv_id)
        return conv

    def _messages(self, conv_id):
        rows = self._conn.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id", (conv_id,)
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["citations"] = _loads(d["citations"], None)
            out.append(d)
        return out

    def rename_conversation(self, conv_id, user_id, title):
        cur = self._write(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (title, _now(), conv_id, user_id),
        )
        return cur.rowcount > 0

    def delete_conversation(self, conv_id, user_id):
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM conversations WHERE id = ? AND user_id = ?", (conv_id, user_id)
            )
            self._conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
            self._conn.commit()
        return cur.rowcount > 0

    def add_message(self, conv_id, role, content, citations=None):
        now = _now()
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO messages (conversation_id, role, content, citations, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (conv_id, role, content,
                 json.dumps(citations, ensure_ascii=False) if citations is not None else None, now),
            )
            self._conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conv_id)
            )
            self._conn.commit()
        return {"id": cur.lastrowid, "conversation_id": conv_id, "role": role,
                "content": content, "citations": citations, "created_at": now}

    def share_conversation(self, conv_id, user_id):
        conv = self._conversation_row(conv_id)
        if not conv or conv["user_id"] != user_id:
            return None
        if conv["share_token"]:
            return conv["share_token"]
        token = secrets.token_urlsafe(16)
        self._write("UPDATE conversations SET share_token = ? WHERE id = ?", (token, conv_id))
        return token

    def get_shared_conversation(self, token):
        row = self._conn.execute(
            "SELECT * FROM conversations WHERE share_token = ?", (token,)
        ).fetchone()
        if not row:
            return None
        conv = dict(row)
        conv["messages"] = self._messages(conv["id"])
        return conv

    # ---- 閱讀看板 ----
    def reading_upsert(self, user_id, paper_id, title, state="to-read", tags=None, note=""):
        if state not in _READING_STATES:
            raise ValueError(f"未知狀態：{state}（可用 {_READING_STATES}）")
        self._write(
            """
            INSERT INTO reading_list (user_id, paper_id, title, state, tags, note, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, paper_id) DO UPDATE SET
                title=excluded.title, state=excluded.state, tags=excluded.tags,
                note=excluded.note, updated_at=excluded.updated_at
            """,
            (user_id, paper_id, title, state,
             json.dumps(list(tags or []), ensure_ascii=False), note, _now()),
        )
        return {"id": paper_id, "title": title, "state": state,
                "tags": list(tags or []), "note": note}

    def reading_items(self, user_id, state=None):
        sql, params = "SELECT * FROM reading_list WHERE user_id = ?", [user_id]
        if state:
            sql += " AND state = ?"
            params.append(state)
        sql += " ORDER BY updated_at DESC"
        out = []
        for r in self._conn.execute(sql, params).fetchall():
            d = dict(r)
            out.append({"id": d["paper_id"], "title": d["title"], "state": d["state"],
                        "tags": _loads(d["tags"], []), "note": d["note"] or ""})
        return out

    def reading_set_state(self, user_id, paper_id, state):
        if state not in _READING_STATES:
            raise ValueError(f"未知狀態：{state}")
        cur = self._write(
            "UPDATE reading_list SET state = ?, updated_at = ? WHERE user_id = ? AND paper_id = ?",
            (state, _now(), user_id, paper_id),
        )
        return cur.rowcount > 0

    def reading_remove(self, user_id, paper_id):
        cur = self._write(
            "DELETE FROM reading_list WHERE user_id = ? AND paper_id = ?", (user_id, paper_id)
        )
        return cur.rowcount > 0

    # ---- 通知偏好 ----
    def get_notification_prefs(self, user_id):
        row = self._conn.execute(
            "SELECT * FROM notification_preferences WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not row:
            return dict(_PREF_DEFAULTS)
        d = dict(row)
        d.pop("user_id", None)
        d["dedupe"] = bool(d["dedupe"])
        d["channels"] = _loads(d["channels"], list(_PREF_DEFAULTS["channels"]))
        return d

    def set_notification_prefs(self, user_id, **fields):
        prefs = self.get_notification_prefs(user_id)
        prefs.update({k: v for k, v in fields.items() if k in _PREF_DEFAULTS})
        self._write(
            """
            INSERT INTO notification_preferences
                (user_id, frequency, hour, minute, timezone, quiet_start, quiet_end,
                 min_score, dedupe, channels)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                frequency=excluded.frequency, hour=excluded.hour, minute=excluded.minute,
                timezone=excluded.timezone, quiet_start=excluded.quiet_start,
                quiet_end=excluded.quiet_end, min_score=excluded.min_score,
                dedupe=excluded.dedupe, channels=excluded.channels
            """,
            (user_id, prefs["frequency"], prefs["hour"], prefs["minute"], prefs["timezone"],
             prefs["quiet_start"], prefs["quiet_end"], prefs["min_score"],
             int(prefs["dedupe"]), json.dumps(prefs["channels"], ensure_ascii=False)),
        )
        return prefs

    # ---- 提醒 ----
    def add_reminder(self, user_id, text, due_at, context=None):
        cur = self._write(
            "INSERT INTO reminders (user_id, text, due_at, context, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (user_id, text, due_at,
             json.dumps(context, ensure_ascii=False) if context else None, _now()),
        )
        return self._reminder(cur.lastrowid)

    def _reminder(self, rid):
        row = self._conn.execute("SELECT * FROM reminders WHERE id = ?", (rid,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["done"] = bool(d["done"])
        d["context"] = _loads(d["context"], None)
        return d

    def list_reminders(self, user_id, include_done=False):
        sql, params = "SELECT id FROM reminders WHERE user_id = ?", [user_id]
        if not include_done:
            sql += " AND done = 0"
        sql += " ORDER BY due_at"
        return [self._reminder(r["id"]) for r in self._conn.execute(sql, params).fetchall()]

    def complete_reminder(self, reminder_id, user_id):
        cur = self._write(
            "UPDATE reminders SET done = 1 WHERE id = ? AND user_id = ?", (reminder_id, user_id)
        )
        return cur.rowcount > 0

    def delete_reminder(self, reminder_id, user_id):
        cur = self._write(
            "DELETE FROM reminders WHERE id = ? AND user_id = ?", (reminder_id, user_id)
        )
        return cur.rowcount > 0

    def due_reminders(self, now_iso):
        rows = self._conn.execute(
            "SELECT id FROM reminders WHERE done = 0 AND due_at <= ? ORDER BY due_at",
            (now_iso,),
        ).fetchall()
        return [self._reminder(r["id"]) for r in rows]

    # ---- 學習路徑 / 技能 ----
    def create_learning_path(self, user_id, topic, items):
        now = _now()
        cur = self._write(
            "INSERT INTO learning_paths (user_id, topic, items, progress, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, topic, json.dumps(items, ensure_ascii=False), "{}", now, now),
        )
        return self._learning_path(cur.lastrowid)

    def _learning_path(self, pid):
        row = self._conn.execute("SELECT * FROM learning_paths WHERE id = ?", (pid,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["items"] = _loads(d["items"], [])
        d["progress"] = _loads(d["progress"], {})
        return d

    def list_learning_paths(self, user_id):
        rows = self._conn.execute(
            "SELECT id FROM learning_paths WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()
        return [self._learning_path(r["id"]) for r in rows]

    def update_learning_path(self, path_id, user_id, **fields):
        allowed = {"topic", "items", "progress"}
        updates = {}
        for k, v in fields.items():
            if k not in allowed:
                continue
            updates[k] = json.dumps(v, ensure_ascii=False) if k in ("items", "progress") else v
        if updates:
            updates["updated_at"] = _now()
            sets = ", ".join(f"{k} = ?" for k in updates)
            cur = self._write(
                f"UPDATE learning_paths SET {sets} WHERE id = ? AND user_id = ?",
                (*updates.values(), path_id, user_id),
            )
            if cur.rowcount == 0:
                return None
        return self._learning_path(path_id)

    def delete_learning_path(self, path_id, user_id):
        cur = self._write(
            "DELETE FROM learning_paths WHERE id = ? AND user_id = ?", (path_id, user_id)
        )
        return cur.rowcount > 0

    def set_skill(self, user_id, skill, level):
        self._write(
            "INSERT INTO user_skills (user_id, skill, level, updated_at) VALUES (?, ?, ?, ?)"
            " ON CONFLICT(user_id, skill) DO UPDATE SET level=excluded.level,"
            " updated_at=excluded.updated_at",
            (user_id, skill, float(level), _now()),
        )
        return {"skill": skill, "level": float(level)}

    def list_skills(self, user_id):
        rows = self._conn.execute(
            "SELECT skill, level, updated_at FROM user_skills WHERE user_id = ? ORDER BY skill",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ---- 健康 / 統計 ----
    def stats(self):
        def _count(table):
            return self._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        return {
            "backend": "sqlite_faiss",
            "papers": _count("papers"),
            "users": _count("users"),
            "conversations": _count("conversations"),
            "interactions": _count("interactions"),
            "feeds": _count("feeds"),
            "vectors": self._vs.index.ntotal if self._vs is not None else None,
        }

    def close(self):
        self._conn.close()
