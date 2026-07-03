// 日/夜主題切換：Primer ThemeProvider 包一層可持久化的 colorMode 狀態。
import { BaseStyles, ThemeProvider } from "@primer/react";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

const THEME_KEY = "ragency.theme";

type Mode = "night" | "day";

interface ThemeModeState {
  mode: Mode;
  toggle: () => void;
}

const ThemeModeContext = createContext<ThemeModeState>({ mode: "night", toggle: () => {} });

export function AppThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<Mode>(
    (localStorage.getItem(THEME_KEY) as Mode) ?? "night",
  );
  const toggle = useCallback(() => {
    setMode((m) => {
      const next = m === "night" ? "day" : "night";
      localStorage.setItem(THEME_KEY, next);
      return next;
    });
  }, []);
  const value = useMemo(() => ({ mode, toggle }), [mode, toggle]);
  return (
    <ThemeModeContext.Provider value={value}>
      <ThemeProvider colorMode={mode} preventSSRMismatch>
        <BaseStyles>{children}</BaseStyles>
      </ThemeProvider>
    </ThemeModeContext.Provider>
  );
}

export function useThemeMode(): ThemeModeState {
  return useContext(ThemeModeContext);
}
