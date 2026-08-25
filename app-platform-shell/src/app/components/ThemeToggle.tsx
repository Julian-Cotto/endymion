import { Kanban, Monitor, Moon, Sparkles, Sun } from "lucide-react";

import { useTheme, type ThemeMode } from "../providers/ThemeProvider";

const LABELS: Record<ThemeMode, string> = {
  auto: "Auto",
  light: "Light",
  dark: "Dark",
  bhacemp: "Bhacemp",
  "jira-dark": "Jira Dark",
};

const ICONS: Record<ThemeMode, typeof Monitor> = {
  auto: Monitor,
  light: Sun,
  dark: Moon,
  bhacemp: Sparkles,
  "jira-dark": Kanban,
};

export function ThemeToggle() {
  const { mode, cycleMode } = useTheme();
  const Icon = ICONS[mode];

  return (
    <button
      type="button"
      onClick={cycleMode}
      className="icon-btn"
      title={`Theme: ${LABELS[mode]} (click to cycle)`}
      aria-label={`Theme: ${LABELS[mode]}. Click to cycle.`}
    >
      <Icon size={16} strokeWidth={1.75} />
    </button>
  );
}
