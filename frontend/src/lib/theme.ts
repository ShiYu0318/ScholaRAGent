// 主題：淺色（稿紙）為預設，沒有手動選過時跟隨系統。寫在 <html data-theme>。
import { useCallback, useEffect, useState } from "react";

const THEME_KEY = "scholaragent.theme";
export type ThemeMode = "light" | "dark";

function initial(): ThemeMode {
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === "light" || saved === "dark") return saved;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function applyInitialTheme() {
  document.documentElement.dataset.theme = initial();
}

export function useTheme(): { mode: ThemeMode; setMode: (m: ThemeMode) => void; toggle: () => void } {
  const [mode, setModeState] = useState<ThemeMode>(initial);
  useEffect(() => {
    document.documentElement.dataset.theme = mode;
  }, [mode]);
  const setMode = useCallback((m: ThemeMode) => {
    localStorage.setItem(THEME_KEY, m);
    setModeState(m);
  }, []);
  const toggle = useCallback(() => setMode(mode === "dark" ? "light" : "dark"), [mode, setMode]);
  return { mode, setMode, toggle };
}
