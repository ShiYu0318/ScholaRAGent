"""FastAPI 應用組裝：CORS、routers、自動 Swagger/ReDoc。

啟動：uv run uvicorn src.api.app:app --reload
文件：http://localhost:8000/docs（Swagger）、/redoc（ReDoc）
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src import config
from src.api.routers import ask as ask_router
from src.api.routers import auth as auth_router
from src.api.routers import conversations as conversations_router
from src.api.routers import health as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="AIR-Agent API",
        description="AI 研究副駕：RAG 問答、GraphRAG、深度研究、文獻工具、個人化推送。",
        version="2.0.0",
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
    return app


app = create_app()
