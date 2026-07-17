import type { ColumnConfig } from "../../types/reports";

const NUMERIC_FORMATS = new Set(["int", "float", "currency", "percent"]);

export function isNumericFormat(fmt?: string): boolean {
  return !!fmt && NUMERIC_FORMATS.has(fmt);
}

/** Turn a raw column key into a friendly label: STORE_NUMBER -> "Store Number".
 * Short all-caps tokens are kept as acronyms (RDO, DM, PPLH, DOW). */
export function humanize(key: string): string {
  return key
    .replace(/[_\-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .split(" ")
    .map((w) =>
      /^[A-Z0-9]{2,4}$/.test(w) ? w : w.charAt(0).toUpperCase() + w.slice(1).toLowerCase(),
    )
    .join(" ");
}

export function columnLabel(key: string, cfg?: ColumnConfig): string {
  return cfg?.label || humanize(key);
}

const NUMERIC_STRING = /^-?\$?\d[\d,]*(\.\d+)?%?$/;

/** True when a column should be treated as numeric (right-aligned, sortable
 * numerically) — either declared via format, or inferred from the data. */
export function looksNumeric(
  fmt: string | undefined,
  sample: unknown[],
): boolean {
  if (fmt) return isNumericFormat(fmt);
  const vals = sample.filter((v) => v !== null && v !== undefined && v !== "");
  if (!vals.length) return false;
  let hits = 0;
  for (const v of vals.slice(0, 25)) {
    if (typeof v === "number") hits++;
    else if (typeof v === "string" && NUMERIC_STRING.test(v.trim())) hits++;
  }
  return hits / Math.min(vals.length, 25) >= 0.8;
}

/** Render a raw cell value per its column's declared format. */
export function formatValue(value: unknown, cfg?: ColumnConfig): string {
  if (value === null || value === undefined || value === "") return "—";
  const fmt = cfg?.format;
  const num = typeof value === "number" ? value : Number(value);
  const isNum = !Number.isNaN(num) && value !== true && value !== false;

  switch (fmt) {
    case "int":
      return isNum ? Math.round(num).toLocaleString() : String(value);
    case "float":
      return isNum ? num.toLocaleString(undefined, { maximumFractionDigits: 2 }) : String(value);
    case "currency":
      return isNum
        ? num.toLocaleString(undefined, { style: "currency", currency: "USD" })
        : String(value);
    case "percent":
      return isNum
        ? (num <= 1 ? num * 100 : num).toLocaleString(undefined, {
            maximumFractionDigits: 1,
          }) + "%"
        : String(value);
    case "date":
    case "datetime":
      return formatDate(value, fmt === "datetime");
    default:
      return String(value);
  }
}

function formatDate(value: unknown, withTime: boolean): string {
  const d = new Date(String(value));
  if (Number.isNaN(d.getTime())) return String(value);
  return withTime ? d.toLocaleString() : d.toLocaleDateString();
}

export function toNumber(value: unknown): number {
  if (typeof value === "number") return Number.isNaN(value) ? 0 : value;
  // tolerate currency/'%'-decorated strings ("$1,564", "25%")
  const n = Number(String(value).replace(/[$,%\s]/g, ""));
  return Number.isNaN(n) ? 0 : n;
}

const COMPACT = new Intl.NumberFormat(undefined, {
  notation: "compact",
  maximumFractionDigits: 1,
});

/** Compact a number for summary tiles: 142880 -> "142.9K", 1980000 -> "$2M". */
export function formatAggregate(value: number, cfg?: ColumnConfig): string {
  const fmt = cfg?.format;
  if (fmt === "currency") {
    return (
      "$" +
      new Intl.NumberFormat(undefined, {
        notation: "compact",
        maximumFractionDigits: 1,
      }).format(value)
    );
  }
  if (fmt === "percent") return formatValue(value, cfg);
  if (fmt === "float") return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  return COMPACT.format(value);
}

export type AggKind = "sum" | "avg" | "min" | "max" | "count";

export function defaultAgg(cfg?: ColumnConfig): AggKind {
  if (cfg?.agg) return cfg.agg;
  const fmt = cfg?.format;
  if (fmt === "float" || fmt === "percent") return "avg";
  return "sum"; // counts / currency / unlabelled measures
}

export function aggregate(values: number[], kind: AggKind): number {
  if (!values.length) return 0;
  switch (kind) {
    case "avg":
      return values.reduce((a, b) => a + b, 0) / values.length;
    case "min":
      return Math.min(...values);
    case "max":
      return Math.max(...values);
    case "count":
      return values.length;
    default:
      return values.reduce((a, b) => a + b, 0);
  }
}
