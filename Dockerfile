# 多階段建置：前端 Vite build → API image（FastAPI 直接服務前端靜態檔）。
# 容器內沿用 monorepo 佈局（/app/backend + /app/frontend/dist），路徑推導與本機一致。
# docker build -t scholaragent . && docker run --env-file backend/.env -p 8000:8000 scholaragent

FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim AS api
# 釘住 uv 版本：latest 會讓建置結果隨時間改變，也擴大供應鏈風險
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /usr/local/bin/
WORKDIR /app/backend

# 依賴層先建，讓程式碼變更不重裝依賴
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/src/ src/
COPY --from=frontend /build/dist /app/frontend/dist

# 以非 root 使用者執行：程式被攻破時無法改動映像內的程式碼或系統檔，
# 只有 data/（volume）可寫。
RUN useradd --system --uid 10001 --home-dir /app --shell /usr/sbin/nologin app \
    && mkdir -p /app/backend/data \
    && chown -R app:app /app/backend/data
USER app

ENV PATH="/app/backend/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/app/backend/data/.cache/huggingface
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
