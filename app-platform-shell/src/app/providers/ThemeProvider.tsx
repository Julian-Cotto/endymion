import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type ThemeMode = "auto" | "light" | "dark" | "bhacemp" | "jira-dark";
export type ResolvedTheme = "light" | "dark" | "bhacemp" | "jira-dark";

const STORAGE_KEY = "platform-shell:theme";
const CYCLE_ORDER: ThemeMode[] = ["auto", "light", "dark", "bhacemp", "jira-dark"];

interface ThemeContextValue {
  mode: ThemeMode;
  resolved: ResolvedTheme;
  setMode: (next: ThemeMode) => void;
  cycleMode: () => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

function readStoredMode(): ThemeMode {
  if (typeof window === "undefined") return "auto";
  const raw = window.localStorage.getItem(STORAGE_KEY);
  return raw === "light" ||
    raw === "dark" ||
    raw === "bhacemp" ||
    raw === "jira-dark" ||
    raw === "auto"
    ? raw
    : "auto";
}

function getSystemTheme(): ResolvedTheme {
  if (typeof window === "undefined" || !window.matchMedia) return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(resolved: ResolvedTheme): void {
  if (typeof document === "undefined") return;
  document.documentElement.dataset.theme = resolved;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(readStoredMode);
  const [systemTheme, setSystemTheme] = useState<ResolvedTheme>(getSystemTheme);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => setSystemTheme(mql.matches ? "dark" : "light");
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  const resolved: ResolvedTheme =
    mode === "auto" ? systemTheme : (mode as ResolvedTheme);

  useEffect(() => {
    applyTheme(resolved);
  }, [resolved]);

  const setMode = useCallback((next: ThemeMode) => {
    setModeState(next);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, next);
    }
  }, []);

  const cycleMode = useCallback(() => {
    const idx = CYCLE_ORDER.indexOf(mode);
    const next = CYCLE_ORDER[(idx + 1) % CYCLE_ORDER.length];
    setMode(next);
  }, [mode, setMode]);

  const value = useMemo(
    () => ({ mode, resolved, setMode, cycleMode }),
    [mode, resolved, setMode, cycleMode],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used inside ThemeProvider.");
  return ctx;
}
