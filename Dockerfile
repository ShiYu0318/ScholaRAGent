# 多階段建置：前端 Vite build → API image（FastAPI 直接服務前端靜態檔）。
# 容器內沿用 monorepo 佈局（/app/backend + /app/frontend/dist），路徑推導與本機一致。
# docker build -t ragency . && docker run --env-file backend/.env -p 8000:8000 ragency

FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim AS api
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
WORKDIR /app/backend

# 依賴層先建，讓程式碼變更不重裝依賴
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/src/ src/
COPY --from=frontend /build/dist /app/frontend/dist

ENV PATH="/app/backend/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
