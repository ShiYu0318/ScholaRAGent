"""FastAPI 應用組裝：CORS、routers、排程器生命週期、自動 Swagger/ReDoc。

啟動：uv run uvicorn src.api.app:app --reload
文件：http://localhost:8000/docs（Swagger）、/redoc（ReDoc）
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src import config
from src.api.routers import ask as ask_router
from src.api.routers import auth as auth_router
from src.api.routers import conversations as conversations_router
from src.api.routers import feeds as feeds_router
from src.api.routers import graph as graph_router
from src.api.routers import insights as insights_router
from src.api.routers import library as library_router
from src.api.routers import health as health_router
from src.api.routers import notifications as notifications_router
from src.api.routers import reminders as reminders_router
from src.api.routers import research as research_router
from src.api.routers import write as write_router


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
    app = FastAPI(
        title="AIR-Agent API",
        description="AI 研究副駕：RAG 問答、GraphRAG、深度研究、文獻工具、個人化推送。",
        version="2.0.0",
        lifespan=_lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router.router)
    app.include_router(health_router.router)
    app.include_router(ask_router.router)
    app.include_router(conversations_router.router)
    app.include_router(graph_router.router)
    app.include_router(research_router.router)
    app.include_router(write_router.router)
    app.include_router(library_router.router)
    app.include_router(feeds_router.router)
    app.include_router(insights_router.router)
    app.include_router(notifications_router.router)
    app.include_router(reminders_router.router)
    return app


app = create_app()
