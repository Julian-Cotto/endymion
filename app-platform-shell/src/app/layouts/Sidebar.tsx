import { Home } from "lucide-react";

import { iconFor } from "../utils/icon";
import type { BootstrapFeature } from "../../platform/contracts/bootstrapResponse";

interface SidebarProps {
  features: BootstrapFeature[];
  selectedFeatureKey: string | null;
  collapsed: boolean;
  onSelectFeature: (feature: BootstrapFeature) => void;
  onGoHome: () => void;
}

/** Nav rail. Collapse toggle lives in the TopBar — this is just the
 *  feature list. On <md viewports the sidebar is a fixed drawer that
 *  slides in/out via the `sidebar-collapsed` transform. */
export function Sidebar({
  features,
  selectedFeatureKey,
  collapsed,
  onSelectFeature,
  onGoHome,
}: SidebarProps) {
  return (
    <aside
      className={collapsed ? "sidebar sidebar-collapsed" : "sidebar"}
      aria-label="Primary navigation"
    >
      <div className="sidebar-section">
        <button
          type="button"
          onClick={onGoHome}
          className={
            selectedFeatureKey === null
              ? "sidebar-link sidebar-link-active"
              : "sidebar-link"
          }
          title="Home"
        >
          <Home size={16} className="sidebar-link-icon" strokeWidth={1.75} />
          <span className="sidebar-label">Home</span>
        </button>
      </div>

      <div className="sidebar-section sidebar-section-grow">
        <span className="sidebar-section-label">Features</span>
        {features.map((feature) => {
          const Icon = iconFor(feature);
          const isActive = feature.featureKey === selectedFeatureKey;
          const label = feature.nav?.label ?? feature.featureKey;
          return (
            <button
              key={feature.featureKey}
              type="button"
              onClick={() => onSelectFeature(feature)}
              className={
                isActive ? "sidebar-link sidebar-link-active" : "sidebar-link"
              }
              title={label}
            >
              <Icon size={16} className="sidebar-link-icon" strokeWidth={1.75} />
              <span className="sidebar-label">{label}</span>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
