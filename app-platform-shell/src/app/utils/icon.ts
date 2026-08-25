import * as Icons from "lucide-react";

import type { BootstrapFeature } from "../../platform/contracts/bootstrapResponse";

export function toIconName(raw: string | null | undefined): string | null {
  if (!raw) return null;
  if (/^[A-Z]/.test(raw)) return raw;
  return raw
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join("");
}

export function iconFor(feature: BootstrapFeature): Icons.LucideIcon {
  const name = toIconName(feature.nav?.icon);
  const lookup = Icons as unknown as Record<string, Icons.LucideIcon>;
  return (name && lookup[name]) || Icons.LayoutGrid;
}
