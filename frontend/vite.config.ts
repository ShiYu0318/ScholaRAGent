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
    // @primer/react 單一套件即 ~740kB（gzip ~177kB），已獨立成 vendor chunk，
    // 無法再拆：放寬預設 500kB 警告線
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      output: {
        // 把重量級依賴拆成獨立 vendor chunk：改動應用程式碼時
        // 使用者瀏覽器仍可沿用快取的 vendor 檔
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          primer: ["@primer/react", "@primer/octicons-react"],
          d3: ["d3"],
          markdown: ["react-markdown", "remark-gfm"],
        },
      },
    },
  },
});
