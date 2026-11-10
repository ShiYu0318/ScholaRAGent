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
        // Vite 8（Rolldown）只接受函式形式
        manualChunks(id: string) {
          if (!id.includes("node_modules")) return undefined;
          if (/node_modules\/(react|react-dom|react-router|react-router-dom|scheduler)\//.test(id)) return "react";
          if (/node_modules\/d3(-[a-z]+)?\//.test(id)) return "d3";
          if (/node_modules\/(react-markdown|remark-|micromark|mdast-|unified|hast-|unist-|vfile)/.test(id)) return "markdown";
          return undefined;
        },
      },
    },
  },
});
