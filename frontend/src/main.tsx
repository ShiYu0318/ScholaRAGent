import React from "react";
import ReactDOM from "react-dom/client";

import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/components.css";
import App from "./App";
import "./i18n";
import { applyInitialTheme } from "./lib/theme";

// 在第一次繪製前套用主題，避免閃一下錯誤的配色
applyInitialTheme();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
