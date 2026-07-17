import type { ReactNode } from "react";

/** Friendly empty state with a simple inline illustration + optional CTA. */
export function EmptyState({
  title,
  hint,
  action,
}: {
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="rl-emptystate">
      <svg width="96" height="96" viewBox="0 0 96 96" fill="none" aria-hidden>
        <rect
          x="16"
          y="20"
          width="64"
          height="56"
          rx="8"
          fill="var(--rl-surface-2)"
          stroke="var(--rl-border)"
          strokeWidth="2"
        />
        <rect x="26" y="46" width="8" height="20" rx="2" fill="var(--rl-primary)" opacity="0.5" />
        <rect x="40" y="38" width="8" height="28" rx="2" fill="var(--rl-primary)" opacity="0.75" />
        <rect x="54" y="30" width="8" height="36" rx="2" fill="var(--rl-primary)" />
        <line x1="24" y1="66" x2="72" y2="66" stroke="var(--rl-border)" strokeWidth="2" />
      </svg>
      <h3>{title}</h3>
      {hint && <p>{hint}</p>}
      {action && <div className="rl-emptystate-action">{action}</div>}
    </div>
  );
}
