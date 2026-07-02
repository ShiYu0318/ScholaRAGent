"""集中讀取專案根目錄 .env 的設定。"""
import os
from pathlib import Path

from dotenv import load_dotenv

# 專案根目錄 = 本檔案的上上層 (src/config.py -> src -> repo root)
ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"
DATA_DIR = ROOT_DIR / "data"

load_dotenv(ENV_PATH)

# --- Groq (OpenAI 相容端點) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# --- Discord ---
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0") or "0")
# 設定後，斜線指令會立即同步到該伺服器（測試用）；留空則走全域同步（最久 1 小時生效）
DISCORD_GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0") or "0")

# --- 爬蟲 / 推送 ---
ARXIV_QUERY = os.getenv("ARXIV_QUERY", "cat:cs.AI")
DAILY_COUNT = int(os.getenv("DAILY_COUNT", "5"))
# 推送時間以本地時區（PUSH_TZ_OFFSET）表示，使用者用 /set_push_time 設定後存入 schedule.json
PUSH_HOUR = int(os.getenv("PUSH_HOUR", "9"))     # 本地時
PUSH_MINUTE = int(os.getenv("PUSH_MINUTE", "0"))  # 本地分
PUSH_TZ_OFFSET = int(os.getenv("PUSH_TZ_OFFSET", "8"))  # 時區偏移（小時），預設 +8 台灣
REPORT_COUNT = int(os.getenv("REPORT_COUNT", "8"))  # 主題報告檢索的論文數

# --- RAG ---
EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
RERANK_ENABLED = os.getenv("RERANK_ENABLED", "0") in ("1", "true", "True")
INDEX_TYPE = os.getenv("INDEX_TYPE", "flat")   # flat（精確）或 hnsw（近似，規模化）
HNSW_M = int(os.getenv("HNSW_M", "32"))         # HNSW 每節點鄰居數
INDEX_PATH = DATA_DIR / "faiss.index"
METADATA_PATH = DATA_DIR / "metadata.json"
SCHEDULE_PATH = DATA_DIR / "schedule.json"  # 持久化使用者設定的推送時間

# --- 關聯式資料庫（SQLite）---
DB_PATH = DATA_DIR / "air_agent.db"

# --- 記憶模組 ---
MEMORY_PATH = DATA_DIR / "memory.json"

# --- 工具呼叫---
TASKS_PATH = DATA_DIR / "tasks.json"

# --- 多平台推送---
# Telegram：BotFather 取得 token；chat_id 可用 @userinfobot 查
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
# Email（SMTP）
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")  # 逗號分隔多個收件者
# LINE Messaging API（LINE Notify 已停用）
LINE_CHANNEL_TOKEN = os.getenv("LINE_CHANNEL_TOKEN", "")
LINE_TO = os.getenv("LINE_TO", "")
# 額外爬蟲
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")  # 選填，提高 GitHub API 額度
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "")  # X (Twitter) API v2，需付費方案

# --- Web API / 認證 ---
# JWT_SECRET 未設定時每次啟動隨機產生（重啟後舊 token 失效，僅適合本機開發）
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))  # 預設 7 天
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
API_PUBLIC_URL = os.getenv("API_PUBLIC_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
# OAuth（金鑰未設定則該登入方式自動隱藏）
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")

# --- 儲存後端：sqlite（本機 SQLite+FAISS）或 postgres（Postgres+pgvector）---
STORE_BACKEND = os.getenv("STORE_BACKEND", "sqlite")
DATABASE_URL = os.getenv("DATABASE_URL", "")  # postgres 後端連線字串

DATA_DIR.mkdir(exist_ok=True)
