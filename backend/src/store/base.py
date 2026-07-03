"""Store 抽象層：關聯資料 + 向量檢索的統一介面。

兩個實作共用同一套 schema 與方法簽名：
- sqlite_faiss：本機開發（SQLite + FAISS），零外部服務。
- postgres_pgvector：部署環境（Postgres + pgvector）。

API 層只依賴本介面，由 `src.store.get_store()` 依設定挑選後端。
既有的 `db.Database` 與 `rag.VectorStore` 邏輯收斂於各實作內，
Discord bot 等舊入口仍可直接使用底層類別，不受影響。
"""
from abc import ABC, abstractmethod


class Store(ABC):
    # ---- 使用者 ----
    @abstractmethod
    def create_user(self, email, password_hash=None, display_name=None,
                    locale="en", google_sub=None, github_id=None, discord_id=None):
        """建立使用者，回傳 user dict；email 重複時丟 ValueError。"""

    @abstractmethod
    def get_user(self, user_id):
        """依 id 取使用者，不存在回傳 None。"""

    @abstractmethod
    def get_user_by_email(self, email):
        """依 email 取使用者（大小寫不敏感），不存在回傳 None。"""

    @abstractmethod
    def get_user_by_oauth(self, field, value):
        """依 OAuth 欄位（google_sub / github_id / discord_id）取使用者。"""

    @abstractmethod
    def update_user(self, user_id, **fields):
        """更新使用者欄位，回傳更新後 user dict。"""

    @abstractmethod
    def all_users(self):
        """列出所有使用者（排程器建立每人任務用）。"""

    # ---- 論文 / 互動（結構化查詢）----
    @abstractmethod
    def upsert_papers(self, papers):
        """批次寫入論文，回傳實際新增數。"""

    @abstractmethod
    def get_paper(self, paper_id):
        """取單篇論文 dict。"""

    @abstractmethod
    def all_papers(self, limit=None, source=None):
        """列出論文（新到舊）。"""

    @abstractmethod
    def count_papers(self):
        """論文總數。"""

    @abstractmethod
    def log_interaction(self, action, paper_id=None, user_id=None, value=1.0):
        """記錄一筆互動事件。"""

    @abstractmethod
    def interaction_counts(self, action=None):
        """{paper_id: 加權互動總分}。"""

    @abstractmethod
    def action_totals(self, user_id=None):
        """{action: 次數}；可限定單一使用者。"""

    @abstractmethod
    def user_interactions(self, user_id, limit=200):
        """某使用者的互動事件（新到舊），供個人分析。"""

    # ---- 向量檢索 ----
    @abstractmethod
    def index_papers(self, papers):
        """把論文加入向量索引（去重），回傳實際新增清單。"""

    @abstractmethod
    def search_scored(self, query, k=4, where=None, rerank=True):
        """語意檢索，回傳 [(paper, score)]，分數越高越相關。"""

    def search(self, query, k=4, where=None, rerank=True):
        return [p for p, _ in self.search_scored(query, k=k, where=where, rerank=rerank)]

    # ---- RSS 訂閱源（feeds）----
    @abstractmethod
    def add_feed(self, user_id, url, title=None, category=None):
        """新增個人 RSS 來源，回傳 feed dict。"""

    @abstractmethod
    def list_feeds(self, user_id):
        """列出個人 RSS 來源。"""

    @abstractmethod
    def update_feed(self, feed_id, user_id, **fields):
        """更新（僅限本人的）feed，回傳更新後 dict 或 None。"""

    @abstractmethod
    def delete_feed(self, feed_id, user_id):
        """刪除（僅限本人的）feed，回傳是否刪除。"""

    # ---- 主題訂閱（keywords）----
    @abstractmethod
    def add_subscription(self, user_id, name, keywords):
        """新增/覆蓋一個主題訂閱。"""

    @abstractmethod
    def list_subscriptions(self, user_id):
        """列出主題訂閱。"""

    @abstractmethod
    def remove_subscription(self, user_id, name):
        """移除主題訂閱，回傳是否存在。"""

    # ---- 對話 ----
    @abstractmethod
    def create_conversation(self, user_id, title=""):
        """建立對話，回傳 conversation dict。"""

    @abstractmethod
    def list_conversations(self, user_id, query=None, limit=50):
        """列出/搜尋對話（依更新時間新到舊）。query 比對標題與訊息內容。"""

    @abstractmethod
    def get_conversation(self, conv_id, user_id=None):
        """取對話（含 messages）；user_id 給定時檢查擁有者。"""

    @abstractmethod
    def rename_conversation(self, conv_id, user_id, title):
        """改對話標題。"""

    @abstractmethod
    def delete_conversation(self, conv_id, user_id):
        """刪對話與其訊息，回傳是否刪除。"""

    @abstractmethod
    def add_message(self, conv_id, role, content, citations=None):
        """在對話尾端加一則訊息，回傳 message dict。"""

    @abstractmethod
    def share_conversation(self, conv_id, user_id):
        """產生（或回傳既有）分享 token。"""

    @abstractmethod
    def get_shared_conversation(self, token):
        """依分享 token 取對話（含 messages），不存在回傳 None。"""

    # ---- 閱讀看板（per-user）----
    @abstractmethod
    def reading_upsert(self, user_id, paper_id, title, state="to-read", tags=None, note=""):
        """加入/更新閱讀項目。"""

    @abstractmethod
    def reading_items(self, user_id, state=None):
        """列出閱讀項目，可篩狀態。"""

    @abstractmethod
    def reading_set_state(self, user_id, paper_id, state):
        """改閱讀狀態，回傳是否存在。"""

    @abstractmethod
    def reading_remove(self, user_id, paper_id):
        """移除閱讀項目，回傳是否存在。"""

    # ---- 通知偏好 ----
    @abstractmethod
    def get_notification_prefs(self, user_id):
        """取通知偏好（未設定回傳預設值）。"""

    @abstractmethod
    def set_notification_prefs(self, user_id, **fields):
        """更新通知偏好，回傳更新後 dict。"""

    # ---- 提醒 ----
    @abstractmethod
    def add_reminder(self, user_id, text, due_at, context=None):
        """新增提醒，回傳 reminder dict。"""

    @abstractmethod
    def list_reminders(self, user_id, include_done=False):
        """列出提醒（依到期時間）。"""

    @abstractmethod
    def complete_reminder(self, reminder_id, user_id):
        """標記完成，回傳是否存在。"""

    @abstractmethod
    def delete_reminder(self, reminder_id, user_id):
        """刪除提醒，回傳是否存在。"""

    @abstractmethod
    def due_reminders(self, now_iso):
        """全體使用者中已到期且未完成的提醒（排程器用）。"""

    # ---- 學習路徑 / 技能 ----
    @abstractmethod
    def create_learning_path(self, user_id, topic, items):
        """建立學習路徑（items 為步驟清單）。"""

    @abstractmethod
    def list_learning_paths(self, user_id):
        """列出學習路徑。"""

    @abstractmethod
    def update_learning_path(self, path_id, user_id, **fields):
        """更新（items / progress / topic），回傳更新後 dict 或 None。"""

    @abstractmethod
    def delete_learning_path(self, path_id, user_id):
        """刪除學習路徑。"""

    @abstractmethod
    def set_skill(self, user_id, skill, level):
        """設定技能等級（0-100）。"""

    @abstractmethod
    def list_skills(self, user_id):
        """列出技能。"""

    # ---- 健康 / 統計 ----
    @abstractmethod
    def stats(self):
        """回傳 {papers, users, conversations, interactions} 等總量統計。"""

    @abstractmethod
    def close(self):
        """釋放連線資源。"""
