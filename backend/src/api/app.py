"""FastAPI 應用組裝：CORS、routers、排程器生命週期、自動 Swagger/ReDoc。

啟動：uv run uvicorn src.api.app:app --reload
文件：http://localhost:8000/docs（Swagger）、/redoc（ReDoc）
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src import config
from src.api import auth as auth_lib
from src.api.middleware import BodySizeLimitMiddleware, SecurityHeadersMiddleware
from src.api.ratelimit import RateLimiter
from src.api.routers import ask as ask_router
from src.api.routers import auth as auth_router
from src.api.routers import conversations as conversations_router
from src.api.routers import documents as documents_router
from src.api.routers import extras as extras_router
from src.api.routers import feeds as feeds_router
from src.api.routers import graph as graph_router
from src.api.routers import insights as insights_router
from src.api.routers import learning as learning_router
from src.api.routers import library as library_router
from src.api.routers import health as health_router
from src.api.routers import notifications as notifications_router
from src.api.routers import projects as projects_router
from src.api.routers import reminders as reminders_router
from src.api.routers import research as research_router
from src.api.routers import write as write_router
from src.utils.logger import get_logger

logger = get_logger("api")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    manager = None
    if config.SCHEDULER_ENABLED:
        from src.scheduler import get_scheduler_manager
        manager = get_scheduler_manager()
        manager.start()
    yield
    if manager is not None:
        manager.stop()


def create_app() -> FastAPI:
    auth_lib.check_production_config()
    app = FastAPI(
        title="ScholaRAGent API",
        description="AI 研究副駕：RAG 問答、GraphRAG、深度研究、文獻工具、個人化推送。",
        version="2.0.0",
        lifespan=_lifespan,
        docs_url="/docs" if config.API_DOCS_ENABLED else None,
        redoc_url="/redoc" if config.API_DOCS_ENABLED else None,
        openapi_url="/openapi.json" if config.API_DOCS_ENABLED else None,
    )
    app.state.limiter = RateLimiter()
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    # 最後加入＝最外層：連 CORS 預檢與 413 回應都帶安全標頭
    app.add_middleware(SecurityHeadersMiddleware)
    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        # 未預期的例外：細節只進日誌，用戶端拿到固定訊息
        logger.error(f"未處理的例外 {request.method} {request.url.path}", exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "伺服器內部錯誤"})

    app.include_router(auth_router.router)
    app.include_router(health_router.router)
    app.include_router(ask_router.router)
    app.include_router(conversations_router.router)
    app.include_router(graph_router.router)
    app.include_router(research_router.router)
    app.include_router(write_router.router)
    app.include_router(library_router.router)
    app.include_router(projects_router.router)
    app.include_router(documents_router.router)
    app.include_router(feeds_router.router)
    app.include_router(insights_router.router)
    app.include_router(notifications_router.router)
    app.include_router(reminders_router.router)
    app.include_router(learning_router.router)
    app.include_router(extras_router.router)

    # 前端 build 產物存在時由 API 直接服務（SPA 用 HashRouter，不需 history
    # fallback）；API 路由已註冊在前，優先於此 mount。monorepo 佈局下 dist
    # 在 backend/ 的兄弟目錄 frontend/（容器內同樣是 /app/frontend/dist）。
    dist = Path(__file__).resolve().parents[3] / "frontend" / "dist"
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app


app = create_app()
