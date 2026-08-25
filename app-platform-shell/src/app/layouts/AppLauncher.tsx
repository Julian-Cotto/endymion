import { useEffect, useRef, useState } from "react";
import { Home, LayoutGrid } from "lucide-react";

import { iconFor } from "../utils/icon";
import type { BootstrapFeature } from "../../platform/contracts/bootstrapResponse";

interface AppLauncherProps {
  features: BootstrapFeature[];
  selectedFeatureKey: string | null;
  onSelectFeature: (feature: BootstrapFeature) => void;
  onGoHome: () => void;
}

/** Microsoft-style "waffle" app launcher. A grid popover of every feature
 *  the user can reach, opened from a button in the TopBar. Used as the
 *  primary app switcher when the shell is in `launcher` nav mode (so the
 *  left rail can be handed to the active feature's own sidebar). */
export function AppLauncher({
  features,
  selectedFeatureKey,
  onSelectFeature,
  onGoHome,
}: AppLauncherProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDocClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const sorted = [...features].sort((l, r) => {
    const lo = l.nav?.order ?? 9999;
    const ro = r.nav?.order ?? 9999;
    if (lo !== ro) return lo - ro;
    return (l.nav?.label ?? l.featureKey).localeCompare(
      r.nav?.label ?? r.featureKey,
    );
  });

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="icon-btn"
        title="App launcher"
        aria-label="Open app launcher"
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <LayoutGrid size={16} strokeWidth={1.75} />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute left-0 top-full mt-1 z-50 w-[300px] rounded-xl
                     border border-border bg-surface shadow-xl p-3"
        >
          <div className="px-1 pb-2 text-center text-[10px] font-semibold uppercase tracking-widest text-text-muted">
            Apps
          </div>
          <div className="grid grid-cols-3 gap-1.5">
            <LauncherTile
              icon={<Home size={20} strokeWidth={1.75} />}
              label="Home"
              active={selectedFeatureKey === null}
              onClick={() => {
                onGoHome();
                setOpen(false);
              }}
            />
            {sorted.map((feature) => {
              const Icon = iconFor(feature);
              return (
                <LauncherTile
                  key={feature.featureKey}
                  icon={<Icon size={20} strokeWidth={1.75} />}
                  label={feature.nav?.label ?? feature.featureKey}
                  active={feature.featureKey === selectedFeatureKey}
                  onClick={() => {
                    onSelectFeature(feature);
                    setOpen(false);
                  }}
                />
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function LauncherTile({
  icon,
  label,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      role="menuitem"
      onClick={onClick}
      title={label}
      className={
        "flex flex-col items-center justify-start gap-2 rounded-lg px-1 py-3 " +
        "text-center transition-colors focus-visible:outline-none " +
        "focus-visible:ring-2 focus-visible:ring-primary " +
        (active
          ? "bg-primary-soft text-primary-soft-fg"
          : "text-text hover:bg-surface-muted")
      }
    >
      <span
        className={
          "flex h-6 items-center justify-center " +
          (active ? "text-primary-soft-fg" : "text-primary")
        }
      >
        {icon}
      </span>
      {/* Reserve two lines so 1- and 2-line labels keep every tile identical
          and the icons line up across the row. */}
      <span className="flex min-h-[28px] w-full items-start justify-center text-[11px] leading-tight line-clamp-2">
        {label}
      </span>
    </button>
  );
}
