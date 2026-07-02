import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// 開發時把 API 請求代理到本機 FastAPI（uv run uvicorn src.api.app:app）
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/auth": "http://localhost:8000",
    },
  },
});
