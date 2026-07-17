import type { CSSProperties } from "react";
import type { ColumnConfig } from "../../types/reports";
import { looksNumeric, toNumber } from "./format";

type Row = Record<string, unknown>;

export interface ColStat {
  numeric: boolean;
  min: number;
  max: number;
  distinct: number;
  measure: boolean; // numeric with spread → data-bar / summary candidate
  badge: boolean; // low-cardinality categorical → pill
}

/** One pass over the rows to decide how each column should be visualized. */
export function analyzeColumns(
  columns: string[],
  rows: Row[],
  cfg: Record<string, ColumnConfig>,
  firstCol: string,
): Record<string, ColStat> {
  const out: Record<string, ColStat> = {};
  for (const c of columns) {
    const vals = rows
      .map((r) => r[c])
      .filter((v) => v !== null && v !== undefined && v !== "");
    const numeric = looksNumeric(cfg[c]?.format, vals);
    const distinctSet = new Set(vals.map((v) => String(v)));
    const distinct = distinctSet.size;

    let min = Infinity;
    let max = -Infinity;
    if (numeric) {
      for (const v of vals) {
        const n = toNumber(v);
        if (n < min) min = n;
        if (n > max) max = n;
      }
    }

    const measure =
      numeric &&
      distinct >= 8 &&
      max > min &&
      c !== firstCol &&
      cfg[c]?.bar !== false;

    const maxLen = Math.max(0, ...[...distinctSet].map((s) => s.length));
    const fmt = cfg[c]?.format;
    const dateLike = fmt === "date" || fmt === "datetime";
    // Auto-badge only short, low-cardinality *categoricals* — never dates,
    // never single-value columns (a badge with one color carries no signal).
    const badge =
      cfg[c]?.style === "badge" ||
      (c !== firstCol &&
        !measure &&
        !dateLike &&
        distinct >= 2 &&
        distinct <= 7 &&
        maxLen <= 8);

    out[c] = {
      numeric,
      min: min === Infinity ? 0 : min,
      max: max === -Infinity ? 0 : max,
      distinct,
      measure,
      badge,
    };
  }
  return out;
}

// ---- Category badges: stable soft color per distinct value --------------
const BADGE_COLORS = [
  "210 90% 60%", // blue
  "150 65% 45%", // green
  "35 90% 55%", // amber
  "265 70% 65%", // violet
  "0 75% 62%", // red
  "190 75% 50%", // cyan
  "320 65% 62%", // pink
];

function hash(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return Math.abs(h);
}

export function badgeStyle(value: unknown): CSSProperties {
  const hsl = BADGE_COLORS[hash(String(value)) % BADGE_COLORS.length];
  return {
    background: `hsl(${hsl} / 0.16)`,
    color: `hsl(${hsl})`,
    borderColor: `hsl(${hsl} / 0.35)`,
  };
}

// ---- Inline data bar: a thin underline scaled to the column max ---------
export function barStyle(value: unknown, stat: ColStat): CSSProperties | undefined {
  if (!stat.measure || stat.max <= 0) return undefined;
  const pct = Math.max(0, Math.min(100, (toNumber(value) / stat.max) * 100));
  return {
    backgroundImage: "linear-gradient(90deg, var(--rl-bar-fill), var(--rl-bar-fill))",
    backgroundRepeat: "no-repeat",
    backgroundPosition: "left bottom",
    backgroundSize: `${pct}% 3px`,
  };
}

// ---- Conditional heat: traffic-light scale (high=good; reverse flips) ---
export function heatBackground(
  value: unknown,
  stat: ColStat,
  heat: boolean | "reverse" | undefined,
): string | undefined {
  if (!heat || !stat.numeric || stat.max <= stat.min) return undefined;
  let t = (toNumber(value) - stat.min) / (stat.max - stat.min);
  if (heat === "reverse") t = 1 - t;
  const hue = Math.round(t * 120); // 0=red → 120=green
  return `hsl(${hue} 70% 45% / 0.22)`;
}
