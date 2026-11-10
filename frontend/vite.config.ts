import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// 開發時把 API 請求代理到本機 FastAPI（cd backend && uv run python main.py api）
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/auth": "http://localhost:8000",
    },
  },
  build: {
    rollupOptions: {
      output: {
        // 重量級依賴拆成獨立 vendor chunk：改動應用程式碼時瀏覽器仍可沿用快取
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          d3: ["d3"],
          markdown: ["react-markdown", "remark-gfm"],
        },
      },
    },
  },
});
