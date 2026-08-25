import { useEffect, useState, type ReactNode } from "react";

import { Sidebar } from "./Sidebar";
import { TopBar, type NavMode } from "./TopBar";
import type { BootstrapFeature } from "../../platform/contracts/bootstrapResponse";
import type { ShellUserSession } from "../../platform/auth/sessionTypes";

const COLLAPSE_KEY = "platform-shell:sidebar-collapsed";
const NAV_MODE_KEY = "platform-shell:nav-mode";
// Nav mode is stored PER APP (keyed by featureKey) so e.g. a feature with a
// rich sidebar of its own can run launcher-only (waffle + its own sidebar as
// primary) while simpler apps keep the classic shell rail.
const HOME_NAV_KEY = "__home__";

function readCollapsed(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(COLLAPSE_KEY) === "1";
}

function readNavModes(): Record<string, NavMode> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(NAV_MODE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    // Ignore the legacy single-string value; start from an empty map.
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    const out: Record<string, NavMode> = {};
    for (const [k, v] of Object.entries(parsed)) {
      if (v === "launcher" || v === "rail") out[k] = v;
    }
    return out;
  } catch {
    return {};
  }
}

interface AppShellProps {
  session: ShellUserSession;
  features: BootstrapFeature[];
  selectedFeature: BootstrapFeature | null;
  selectedFeatureKey: string | null;
  onSelectFeature: (feature: BootstrapFeature) => void;
  onGoHome: () => void;
  onLogout?: () => void;
  children: ReactNode;
}

export function AppShell({
  session,
  features,
  selectedFeature,
  selectedFeatureKey,
  onSelectFeature,
  onGoHome,
  onLogout,
  children,
}: AppShellProps) {
  const [collapsed, setCollapsed] = useState<boolean>(readCollapsed);
  const [navModes, setNavModes] = useState<Record<string, NavMode>>(readNavModes);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(COLLAPSE_KEY, collapsed ? "1" : "0");
  }, [collapsed]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(NAV_MODE_KEY, JSON.stringify(navModes));
  }, [navModes]);

  // Which app's mode are we editing/reading right now?
  const currentNavKey = selectedFeatureKey ?? HOME_NAV_KEY;
  const navMode: NavMode = navModes[currentNavKey] ?? "rail";

  const toggleCollapse = () => setCollapsed((c) => !c);
  const toggleNavMode = () =>
    setNavModes((prev) => ({
      ...prev,
      [currentNavKey]: navMode === "rail" ? "launcher" : "rail",
    }));
  const closeOnMobile = () => setCollapsed(true);

  // In launcher mode the shell hands its left column to the active feature's
  // own sidebar (rendered inside `children`); the app switcher moves to the
  // TopBar waffle. Rail mode keeps the classic app rail.
  const showRail = navMode === "rail";

  return (
    <div className="shell-frame bg-bg text-text font-sans">
      <TopBar
        session={session}
        features={features}
        selectedFeature={selectedFeature}
        selectedFeatureKey={selectedFeatureKey}
        collapsed={collapsed}
        navMode={navMode}
        onToggleCollapse={toggleCollapse}
        onToggleNavMode={toggleNavMode}
        onSelectFeature={onSelectFeature}
        onGoHome={onGoHome}
        onLogout={onLogout}
      />

      <div className="shell-body">
        {/* Mobile drawer backdrop — visible only when sidebar is open
            on <md (sidebar-backdrop already scopes itself with md:hidden). */}
        {showRail && !collapsed && (
          <div
            className="sidebar-backdrop"
            onClick={closeOnMobile}
            aria-hidden="true"
          />
        )}

        {showRail && (
          <Sidebar
            features={features}
            selectedFeatureKey={selectedFeatureKey}
            collapsed={collapsed}
            onSelectFeature={onSelectFeature}
            onGoHome={onGoHome}
          />
        )}

        <main className="shell-main page-body">{children}</main>
      </div>
    </div>
  );
}
