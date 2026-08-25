import { useMemo } from "react";
import * as Icons from "lucide-react";

import type { BootstrapResponse, BootstrapFeature } from "../../platform/contracts/bootstrapResponse";
import type { ShellUserSession } from "../../platform/auth/sessionTypes";

interface HomePageProps {
  runtime: BootstrapResponse | null;
  session: ShellUserSession;
  onLaunchFeature: (feature: BootstrapFeature) => void;
}

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 5) return "Working late";
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  if (h < 21) return "Good evening";
  return "Working late";
}

function toIconName(raw: string | null | undefined): string | null {
  if (!raw) return null;
  // chad uses PascalCase lucide names. Be tolerant of kebab-case too.
  if (/^[A-Z]/.test(raw)) return raw;
  return raw
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join("");
}

export function HomePage({ runtime, session, onLaunchFeature }: HomePageProps) {
  const features = useMemo(() => {
    const list = runtime?.features ?? [];
    return [...list].sort((l, r) => {
      const lo = l.nav?.order ?? 9999;
      const ro = r.nav?.order ?? 9999;
      if (lo !== ro) return lo - ro;
      return (l.nav?.label ?? l.featureKey).localeCompare(r.nav?.label ?? r.featureKey);
    });
  }, [runtime]);

  const stats = useMemo(
    () => [
      { label: "Features available", value: features.length },
      { label: "Roles assigned", value: session.roles?.length ?? 0 },
      { label: "Permissions", value: runtime?.permissions?.length ?? 0 },
      { label: "Environment", value: runtime?.environment ?? "—" },
    ],
    [features.length, session.roles, runtime],
  );

  const firstName =
    session.userName?.split(/[\s.]+/)[0] ?? session.email?.split("@")[0] ?? "there";

  return (
    <div className="stack-lg max-w-6xl mx-auto w-full">
      <header className="hero">
        <h1 className="hero-title">
          {getGreeting()}, {firstName}
        </h1>
        <p className="hero-subtitle">
          Pick a feature below to get started, or use the topbar to navigate.
        </p>
      </header>

      <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {stats.map((s) => (
          <div key={s.label} className="stat">
            <span className="stat-value">{s.value}</span>
            <span className="stat-label">{s.label}</span>
          </div>
        ))}
      </section>

      <section className="section-card">
        <div className="section-card-header">
          <Icons.LayoutGrid size={16} className="text-primary shrink-0" />
          <h2 className="heading-3 flex-1">My Features</h2>
          <span className="badge">{features.length}</span>
        </div>
        <div className="section-card-body">
          {features.length === 0 ? (
            <div className="alert alert-warning">
              No features are available for this user/environment.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {features.map((feature) => {
                const iconName = toIconName(feature.nav?.icon);
                const IconComp =
                  (iconName && (Icons as unknown as Record<string, Icons.LucideIcon>)[iconName]) ||
                  Icons.LayoutGrid;
                return (
                  <button
                    key={feature.featureKey}
                    type="button"
                    onClick={() => onLaunchFeature(feature)}
                    className="feature-tile group text-left"
                  >
                    <div className="feature-tile-row">
                      <span className="feature-tile-icon">
                        <IconComp size={18} strokeWidth={1.75} />
                      </span>
                      <div className="flex flex-col flex-1 min-w-0">
                        <span className="feature-tile-title">
                          {feature.displayName ?? feature.nav?.label ?? feature.featureKey}
                        </span>
                        <span className="feature-tile-meta">v{feature.version}</span>
                      </div>
                      <Icons.ArrowUpRight
                        size={14}
                        className="text-text-muted shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                      />
                    </div>
                    <p className="feature-tile-desc">
                      {feature.nav?.label ?? feature.featureKey} · {feature.route}
                    </p>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
