"""研究工作區的儲存邏輯：專案、專案文獻、產出文件。

兩個後端的 SQL 幾乎相同，所以寫成共用 mixin；各後端只需提供三個轉接函式：
- `_q(sql, params)`   查詢，回傳 list[dict]
- `_x(sql, params)`   寫入，回傳受影響列數
- `_ins(sql, params)` 新增一列，回傳新 id
SQL 一律用 `?` 佔位符（Postgres 轉接層會換成 `%s`）。

所有讀寫都以 user_id 限定擁有者：拿別人的 id 來查，一律當作不存在。
"""
import json
from datetime import datetime, timezone

PROJECT_STATUSES = ("active", "archived")
READING_STATES = ("to-read", "reading", "done")
DOCUMENT_KINDS = ("note", "review", "report", "comparison", "deep_research",
                  "outline", "draft")

# {pk} 由各後端代入自己的自動遞增主鍵語法
WORKSPACE_SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id         {pk},
    user_id    INTEGER NOT NULL,
    name       TEXT NOT NULL,
    question   TEXT DEFAULT '',
    status     TEXT DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id);
CREATE TABLE IF NOT EXISTS project_papers (
    project_id INTEGER NOT NULL,
    paper_id   TEXT NOT NULL,
    added_at   TEXT NOT NULL,
    PRIMARY KEY (project_id, paper_id)
);
CREATE TABLE IF NOT EXISTS documents (
    id         {pk},
    user_id    INTEGER NOT NULL,
    project_id INTEGER,
    kind       TEXT DEFAULT 'note',
    title      TEXT NOT NULL,
    content    TEXT DEFAULT '',
    paper_ids  TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id)
"""


def _now():
    return datetime.now(timezone.utc).isoformat()


def _ids(text):
    try:
        value = json.loads(text) if text else []
    except (TypeError, ValueError):
        return []
    return value if isinstance(value, list) else []


class WorkspaceMixin:
    # ---- 專案 ----
    def create_project(self, user_id, name, question=""):
        now = _now()
        pid = self._ins(
            "INSERT INTO projects (user_id, name, question, status, created_at, updated_at)"
            " VALUES (?, ?, ?, 'active', ?, ?)",
            (user_id, name, question or "", now, now))
        return self.get_project(pid, user_id)

    def get_project(self, project_id, user_id):
        rows = self._q("SELECT * FROM projects WHERE id = ? AND user_id = ?",
                       (project_id, user_id))
        return self._with_counts(rows[0]) if rows else None

    def list_projects(self, user_id, include_archived=False):
        sql = "SELECT * FROM projects WHERE user_id = ?"
        if not include_archived:
            sql += " AND status = 'active'"
        sql += " ORDER BY updated_at DESC"
        return [self._with_counts(r) for r in self._q(sql, (user_id,))]

    def _with_counts(self, project):
        pid = project["id"]
        project["paper_count"] = self._q(
            "SELECT COUNT(*) AS n FROM project_papers WHERE project_id = ?", (pid,))[0]["n"]
        project["document_count"] = self._q(
            "SELECT COUNT(*) AS n FROM documents WHERE project_id = ?", (pid,))[0]["n"]
        project["conversation_count"] = self._q(
            "SELECT COUNT(*) AS n FROM conversations WHERE project_id = ?", (pid,))[0]["n"]
        return project

    def update_project(self, project_id, user_id, **fields):
        updates = {k: v for k, v in fields.items()
                   if k in ("name", "question", "status") and v is not None}
        if "status" in updates and updates["status"] not in PROJECT_STATUSES:
            raise ValueError("未知的專案狀態")
        if updates:
            sets = ", ".join(f"{k} = ?" for k in updates)
            self._x(f"UPDATE projects SET {sets}, updated_at = ? WHERE id = ? AND user_id = ?",
                    (*updates.values(), _now(), project_id, user_id))
        return self.get_project(project_id, user_id)

    def delete_project(self, project_id, user_id):
        """刪除專案。文獻連結一併移除；文件與對話保留，只解除歸屬。"""
        if not self._x("DELETE FROM projects WHERE id = ? AND user_id = ?",
                       (project_id, user_id)):
            return False
        self._x("DELETE FROM project_papers WHERE project_id = ?", (project_id,))
        self._x("UPDATE documents SET project_id = NULL WHERE project_id = ?", (project_id,))
        self._x("UPDATE conversations SET project_id = NULL WHERE project_id = ?",
                (project_id,))
        return True

    def _touch_project(self, project_id):
        self._x("UPDATE projects SET updated_at = ? WHERE id = ?", (_now(), project_id))

    # ---- 專案文獻 ----
    def project_add_papers(self, project_id, user_id, paper_ids):
        """把已入庫的論文加入專案，回傳實際新增數；專案不屬於該使用者回傳 None。"""
        if self.get_project(project_id, user_id) is None:
            return None
        added = 0
        for paper_id in dict.fromkeys(paper_ids):
            if self.get_paper(paper_id) is None:
                continue
            added += self._x(
                "INSERT INTO project_papers (project_id, paper_id, added_at) VALUES (?, ?, ?)"
                " ON CONFLICT (project_id, paper_id) DO NOTHING",
                (project_id, paper_id, _now()))
        if added:
            self._touch_project(project_id)
        return added

    def project_remove_paper(self, project_id, user_id, paper_id):
        if self.get_project(project_id, user_id) is None:
            return False
        removed = self._x(
            "DELETE FROM project_papers WHERE project_id = ? AND paper_id = ?",
            (project_id, paper_id)) > 0
        if removed:
            self._touch_project(project_id)
        return removed

    def project_paper_ids(self, project_id, user_id):
        if self.get_project(project_id, user_id) is None:
            return None
        rows = self._q(
            "SELECT paper_id FROM project_papers WHERE project_id = ? ORDER BY added_at DESC",
            (project_id,))
        return [r["paper_id"] for r in rows]

    def project_papers(self, project_id, user_id):
        ids = self.project_paper_ids(project_id, user_id)
        if ids is None:
            return None
        return self.get_papers(ids)

    def get_papers(self, paper_ids):
        """依序取多篇論文，略過不存在的 id。"""
        return [p for pid in paper_ids if (p := self.get_paper(pid))]

    # ---- 閱讀清單：局部更新 ----
    def reading_update(self, user_id, paper_id, state=None, tags=None, note=None):
        """只更新有給的欄位（狀態 / 標籤 / 筆記），回傳是否有該項目。"""
        updates = {}
        if state is not None:
            if state not in READING_STATES:
                raise ValueError("未知的閱讀狀態")
            updates["state"] = state
        if tags is not None:
            updates["tags"] = json.dumps(list(tags), ensure_ascii=False)
        if note is not None:
            updates["note"] = note
        if not updates:
            return bool(self._q(
                "SELECT 1 AS x FROM reading_list WHERE user_id = ? AND paper_id = ?",
                (user_id, paper_id)))
        sets = ", ".join(f"{k} = ?" for k in updates)
        return self._x(
            f"UPDATE reading_list SET {sets}, updated_at = ? WHERE user_id = ? AND paper_id = ?",
            (*updates.values(), _now(), user_id, paper_id)) > 0

    # ---- 產出文件 ----
    def create_document(self, user_id, title, content="", kind="note",
                        project_id=None, paper_ids=None):
        if kind not in DOCUMENT_KINDS:
            raise ValueError("未知的文件類型")
        if project_id is not None and self.get_project(project_id, user_id) is None:
            raise ValueError("專案不存在")
        now = _now()
        doc_id = self._ins(
            "INSERT INTO documents (user_id, project_id, kind, title, content, paper_ids,"
            " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, project_id, kind, title, content or "",
             json.dumps(list(paper_ids or [])), now, now))
        if project_id is not None:
            self._touch_project(project_id)
        return self.get_document(doc_id, user_id)

    @staticmethod
    def _document(row, with_content=True):
        row["paper_ids"] = _ids(row.get("paper_ids"))
        if not with_content:
            row["excerpt"] = (row.pop("content", "") or "")[:200]
        return row

    def get_document(self, doc_id, user_id):
        rows = self._q("SELECT * FROM documents WHERE id = ? AND user_id = ?",
                       (doc_id, user_id))
        return self._document(rows[0]) if rows else None

    def list_documents(self, user_id, project_id=None):
        """清單不含全文（只給 200 字摘錄），避免一次載入所有草稿。"""
        sql, params = "SELECT * FROM documents WHERE user_id = ?", [user_id]
        if project_id is not None:
            sql += " AND project_id = ?"
            params.append(project_id)
        sql += " ORDER BY updated_at DESC"
        return [self._document(r, with_content=False) for r in self._q(sql, tuple(params))]

    def update_document(self, doc_id, user_id, **fields):
        updates = {k: v for k, v in fields.items()
                   if k in ("title", "content", "kind", "paper_ids") and v is not None}
        if "kind" in updates and updates["kind"] not in DOCUMENT_KINDS:
            raise ValueError("未知的文件類型")
        if "paper_ids" in updates:
            updates["paper_ids"] = json.dumps(list(updates["paper_ids"]))
        if "project_id" in fields:      # 允許明確設為 None（移出專案）
            pid = fields["project_id"]
            if pid is not None and self.get_project(pid, user_id) is None:
                raise ValueError("專案不存在")
            updates["project_id"] = pid
        if updates:
            sets = ", ".join(f"{k} = ?" for k in updates)
            self._x(f"UPDATE documents SET {sets}, updated_at = ? WHERE id = ? AND user_id = ?",
                    (*updates.values(), _now(), doc_id, user_id))
        return self.get_document(doc_id, user_id)

    def delete_document(self, doc_id, user_id):
        return self._x("DELETE FROM documents WHERE id = ? AND user_id = ?",
                       (doc_id, user_id)) > 0
