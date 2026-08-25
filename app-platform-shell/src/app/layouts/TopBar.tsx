import {
  Home,
  LogOut,
  Menu,
  PanelLeft,
  PanelLeftClose,
  Search,
} from "lucide-react";

import { AppLauncher } from "./AppLauncher";
import { ThemeToggle } from "../components/ThemeToggle";
import { getInitials } from "../utils/initials";
import type { BootstrapFeature } from "../../platform/contracts/bootstrapResponse";
import type { ShellUserSession } from "../../platform/auth/sessionTypes";

export type NavMode = "rail" | "launcher";

interface TopBarProps {
  session: ShellUserSession;
  features: BootstrapFeature[];
  selectedFeature: BootstrapFeature | null;
  selectedFeatureKey: string | null;
  collapsed: boolean;
  navMode: NavMode;
  onToggleCollapse: () => void;
  onToggleNavMode: () => void;
  onSelectFeature: (feature: BootstrapFeature) => void;
  onGoHome: () => void;
  onLogout?: () => void;
}

/** 48px header bar — always visible. Holds the sidebar collapse toggle
 *  (Jira pattern), brand link, search, current-feature breadcrumb,
 *  theme toggle, avatar, and sign-out. */
export function TopBar({
  session,
  features,
  selectedFeature,
  selectedFeatureKey,
  collapsed,
  navMode,
  onToggleCollapse,
  onToggleNavMode,
  onSelectFeature,
  onGoHome,
  onLogout,
}: TopBarProps) {
  const initials = getInitials(session);
  const featureLabel = selectedFeature?.nav?.label ?? selectedFeature?.featureKey ?? null;

  return (
    <header className="topbar">
      <div className="topbar-section">
        {/* Waffle is the app switcher ONLY in launcher mode — in rail mode
            the rail already switches apps, so showing both would compete. */}
        {navMode === "launcher" && (
          <AppLauncher
            features={features}
            selectedFeatureKey={selectedFeatureKey}
            onSelectFeature={onSelectFeature}
            onGoHome={onGoHome}
          />
        )}

        {/* Rail collapse toggle only applies when the shell rail is shown. */}
        {navMode === "rail" && (
          <button
            type="button"
            onClick={onToggleCollapse}
            className="icon-btn"
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-expanded={!collapsed}
          >
            {collapsed ? (
              <Menu size={16} strokeWidth={1.75} />
            ) : (
              <PanelLeftClose size={16} strokeWidth={1.75} />
            )}
          </button>
        )}

        <button
          type="button"
          onClick={onGoHome}
          className="topbar-brand cursor-pointer"
          aria-label="Go to home"
        >
          <Home size={16} className="text-primary" strokeWidth={1.75} />
          <span>App Platform</span>
        </button>

        {featureLabel && (
          <span className="topbar-feature-label">/ {featureLabel}</span>
        )}
      </div>

      <div className="topbar-search-wrap">
        <Search size={14} className="topbar-search-icon" strokeWidth={1.75} />
        <input
          type="search"
          className="topbar-search-input"
          placeholder="Search…"
          aria-label="Search"
        />
      </div>

      <div className="topbar-spacer" />

      <div className="topbar-section">
        <button
          type="button"
          onClick={onToggleNavMode}
          className={navMode === "launcher" ? "icon-btn icon-btn-active" : "icon-btn"}
          title={
            navMode === "rail"
              ? "Switch to app-launcher nav (hide rail, give the left column to the app)"
              : "Switch to rail nav (show the app rail)"
          }
          aria-label="Toggle navigation mode"
          aria-pressed={navMode === "launcher"}
        >
          <PanelLeft size={16} strokeWidth={1.75} />
        </button>
        <ThemeToggle />
        <div
          className="avatar avatar-sm"
          title={session.email ?? session.userName ?? session.userId}
          aria-label={`Signed in as ${session.userName ?? session.email ?? session.userId}`}
        >
          {initials}
        </div>
        {onLogout ? (
          <button
            type="button"
            onClick={onLogout}
            className="icon-btn"
            title="Sign out"
            aria-label="Sign out"
          >
            <LogOut size={16} strokeWidth={1.75} />
          </button>
        ) : null}
      </div>
    </header>
  );
}
