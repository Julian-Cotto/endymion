import { useEffect, useRef, useState } from "react";
import type {
  ChartConfig,
  ChartType,
  ColumnConfig,
  ParamSpec,
  ParamType,
} from "../../types/reports";

export interface MetaShape {
  columns: Record<string, ColumnConfig>;
  params: Record<string, ParamSpec>;
  chart: ChartConfig | null;
}

interface Props extends MetaShape {
  /** Column keys offered to the chart pickers + detected from preview. */
  columnKeys: string[];
  /** Preview sample rows, used to infer formats when detecting columns. */
  sampleRows: Array<Record<string, unknown>>;
  onChange: (next: MetaShape) => void;
}

type ColEntry = [string, ColumnConfig];

const FORMATS = ["", "text", "int", "float", "currency", "percent", "date", "datetime"];
const ALIGNS = ["", "left", "right", "center"];
const AGGS = ["", "sum", "avg", "min", "max", "count"];
const PARAM_TYPES: ParamType[] = ["string", "int", "float", "bool", "date"];
const CHART_TYPES: ChartType[] = ["bar", "line", "pie", "area"];

// --- format inference (used when detecting columns from a preview) ---
const CURRENCY_RE = /amount|price|cost|premium|revenue|paid|total|balance|fee|gross|net/i;
const PERCENT_RE = /ratio|rate|percent|pct/i;

function titleCase(key: string): string {
  return key.replace(/[_-]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function inferFormat(key: string, rows: Array<Record<string, unknown>>): string | undefined {
  const vals = rows.map((r) => r[key]).filter((v) => v !== null && v !== undefined && v !== "");
  if (!vals.length) return undefined;
  const allNumeric = vals.every(
    (v) => typeof v === "number" || (typeof v === "string" && v.trim() !== "" && !Number.isNaN(Number(v))),
  );
  if (allNumeric) {
    const nums = vals.map((v) => Number(v));
    if (PERCENT_RE.test(key) && nums.every((n) => n >= 0 && n <= 1)) return "percent";
    if (CURRENCY_RE.test(key)) return "currency";
    return nums.every((n) => Number.isInteger(n)) ? "int" : "float";
  }
  const allDates = vals.every(
    (v) => typeof v === "string" && /^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2})?/.test(v),
  );
  if (allDates) {
    return vals.some((v) => /[ T]\d{2}:\d{2}/.test(String(v))) ? "datetime" : "date";
  }
  return "text";
}

function inferCfg(key: string, rows: Array<Record<string, unknown>>): ColumnConfig {
  const cfg: ColumnConfig = { label: titleCase(key) };
  const fmt = inferFormat(key, rows);
  if (fmt) cfg.format = fmt;
  return cfg;
}

// --- Record<key, T> helpers (params) ---
function renameKey<T>(obj: Record<string, T>, index: number, key: string): Record<string, T> {
  const entries = Object.entries(obj);
  entries[index] = [key, entries[index][1]];
  return Object.fromEntries(entries);
}
function patchValue<T>(obj: Record<string, T>, index: number, patch: Partial<T>): Record<string, T> {
  const entries = Object.entries(obj);
  entries[index] = [entries[index][0], { ...entries[index][1], ...patch }];
  return Object.fromEntries(entries);
}
function removeAt<T>(obj: Record<string, T>, index: number): Record<string, T> {
  return Object.fromEntries(Object.entries(obj).filter((_, i) => i !== index));
}
function uniqueKey(taken: Set<string>, base: string): string {
  if (!taken.has(base)) return base;
  let n = 2;
  while (taken.has(`${base}_${n}`)) n += 1;
  return `${base}_${n}`;
}

export function MetadataEditor({
  columns,
  params,
  chart,
  columnKeys,
  sampleRows,
  onChange,
}: Props) {
  // Columns are edited as an ORDERED ARRAY so keys can be reordered and transient
  // duplicate/blank keys can be flagged (a Record would silently collapse them).
  const [cols, setCols] = useState<ColEntry[]>(() => Object.entries(columns));
  const [dragIdx, setDragIdx] = useState<number | null>(null);
  const lastEmit = useRef<string>("");

  // Reseed from the prop only on external changes (Advanced JSON edits, etc.),
  // not from our own emits (which round-trip back through the parent).
  useEffect(() => {
    const sig = JSON.stringify(columns);
    if (sig !== lastEmit.current) setCols(Object.entries(columns));
  }, [columns]);

  function emitCols(next: ColEntry[]) {
    setCols(next);
    const obj = Object.fromEntries(next); // duplicate keys collapse in storage
    lastEmit.current = JSON.stringify(obj);
    onChange({ columns: obj, params, chart });
  }
  const setColKey = (i: number, key: string) =>
    emitCols(cols.map((e, idx) => (idx === i ? [key, e[1]] : e)));
  const setColCfg = (i: number, patch: Partial<ColumnConfig>) =>
    emitCols(cols.map((e, idx) => (idx === i ? [e[0], { ...e[1], ...patch }] : e)));
  const removeCol = (i: number) => emitCols(cols.filter((_, idx) => idx !== i));
  const moveCol = (from: number, to: number) => {
    if (from === to) return;
    const next = [...cols];
    const [m] = next.splice(from, 1);
    next.splice(to, 0, m);
    emitCols(next);
  };

  const colKeys = cols.map(([k]) => k).filter(Boolean);
  const detectable = columnKeys.filter((k) => !colKeys.includes(k));
  const pickerKeys = Array.from(new Set([...colKeys, ...columnKeys]));

  function addColumn() {
    emitCols([...cols, [uniqueKey(new Set(cols.map(([k]) => k)), "column"), {}]]);
  }
  function detectColumns() {
    emitCols([...cols, ...detectable.map((k): ColEntry => [k, inferCfg(k, sampleRows)])]);
  }

  // Key-quality warnings.
  const blankCount = cols.filter(([k]) => !k.trim()).length;
  const seen = new Set<string>();
  const dupes = new Set<string>();
  for (const [k] of cols) {
    const t = k.trim();
    if (t) {
      if (seen.has(t)) dupes.add(t);
      seen.add(t);
    }
  }

  // --- params (kept as a plain Record; no reorder needed) ---
  const setParams = (next: Record<string, ParamSpec>) => onChange({ columns, params: next, chart });
  const paramEntries = Object.entries(params);

  // --- chart ---
  const yList: string[] = chart
    ? Array.isArray(chart.y)
      ? chart.y
      : chart.y
        ? [chart.y]
        : []
    : [];
  function setChart(patch: Partial<ChartConfig> | null) {
    if (patch === null) return onChange({ columns, params, chart: null });
    const base: ChartConfig = chart ?? { type: "bar", x: pickerKeys[0] ?? "", y: [] };
    onChange({ columns, params, chart: { ...base, ...patch } });
  }
  function toggleY(key: string) {
    const next = yList.includes(key) ? yList.filter((k) => k !== key) : [...yList, key];
    setChart({ y: next.length === 1 ? next[0] : next });
  }

  return (
    <div className="rl-metaedit">
      {/* -------------------- Columns -------------------- */}
      <details open className="rl-meta-section">
        <summary className="rl-meta-summary">Columns</summary>
        <div className="rl-meta-body">
          <div className="rl-meta-actions">
            <span className="rl-hint">
              Label, number format, alignment, and an optional summary aggregate per
              result column. Drag <span className="rl-drag">⠿</span> or use ▲▼ to reorder.
            </span>
            <div className="rl-actions">
              {detectable.length > 0 && (
                <button type="button" className="rl-btn" onClick={detectColumns}>
                  Detect from preview ({detectable.length})
                </button>
              )}
              <button type="button" className="rl-btn" onClick={addColumn}>
                + Add column
              </button>
            </div>
          </div>

          {cols.length === 0 ? (
            <span className="rl-hint">
              No columns yet. Add one, or click “Preview data” then “Detect from preview”.
            </span>
          ) : (
            <div className="rl-grid-scroll">
              <div className="rl-col-head">
                <span />
                <span>Key</span>
                <span>Label</span>
                <span>Format</span>
                <span>Align</span>
                <span>Agg</span>
                <span>Hide</span>
                <span />
              </div>
              {cols.map(([key, cfg], i) => (
                <div
                  key={i}
                  className={`rl-col-row${dragIdx === i ? " rl-dragging" : ""}`}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={() => {
                    if (dragIdx !== null) moveCol(dragIdx, i);
                    setDragIdx(null);
                  }}
                >
                  <span className="rl-reorder">
                    <span
                      className="rl-drag"
                      draggable
                      onDragStart={() => setDragIdx(i)}
                      onDragEnd={() => setDragIdx(null)}
                      title="Drag to reorder"
                    >
                      ⠿
                    </span>
                    <span className="rl-move">
                      <button
                        type="button"
                        onClick={() => moveCol(i, i - 1)}
                        disabled={i === 0}
                        aria-label="Move column up"
                        title="Move up"
                      >
                        ▲
                      </button>
                      <button
                        type="button"
                        onClick={() => moveCol(i, i + 1)}
                        disabled={i === cols.length - 1}
                        aria-label="Move column down"
                        title="Move down"
                      >
                        ▼
                      </button>
                    </span>
                  </span>
                  <input
                    className="rl-meta-key"
                    value={key}
                    onChange={(e) => setColKey(i, e.target.value)}
                    placeholder="column_key"
                    aria-label="Column key"
                  />
                  <input
                    value={cfg.label ?? ""}
                    onChange={(e) => setColCfg(i, { label: e.target.value })}
                    placeholder="Label"
                    aria-label="Column label"
                  />
                  <select
                    value={cfg.format ?? ""}
                    onChange={(e) => setColCfg(i, { format: e.target.value || undefined })}
                    aria-label="Format"
                  >
                    {FORMATS.map((f) => (
                      <option key={f} value={f}>
                        {f || "—"}
                      </option>
                    ))}
                  </select>
                  <select
                    value={cfg.align ?? ""}
                    onChange={(e) =>
                      setColCfg(i, { align: (e.target.value || undefined) as ColumnConfig["align"] })
                    }
                    aria-label="Align"
                  >
                    {ALIGNS.map((a) => (
                      <option key={a} value={a}>
                        {a || "—"}
                      </option>
                    ))}
                  </select>
                  <select
                    value={cfg.agg ?? ""}
                    onChange={(e) =>
                      setColCfg(i, { agg: (e.target.value || undefined) as ColumnConfig["agg"] })
                    }
                    aria-label="Summary aggregate"
                  >
                    {AGGS.map((a) => (
                      <option key={a} value={a}>
                        {a || "—"}
                      </option>
                    ))}
                  </select>
                  <span className="rl-cell-center">
                    <input
                      type="checkbox"
                      checked={cfg.hidden ?? false}
                      onChange={(e) => setColCfg(i, { hidden: e.target.checked })}
                      aria-label="Hidden"
                    />
                  </span>
                  <span className="rl-cell-center">
                    <button
                      type="button"
                      className="rl-btn rl-btn-sm"
                      onClick={() => removeCol(i)}
                      title="Remove column"
                    >
                      ✕
                    </button>
                  </span>
                </div>
              ))}
            </div>
          )}

          {blankCount > 0 && (
            <div className="rl-warn">
              {blankCount} column{blankCount > 1 ? "s have" : " has"} a blank key — it
              won’t render.
            </div>
          )}
          {dupes.size > 0 && (
            <div className="rl-warn">
              Duplicate key{dupes.size > 1 ? "s" : ""}: {[...dupes].join(", ")} — only the
              last is saved.
            </div>
          )}
        </div>
      </details>

      {/* -------------------- Params -------------------- */}
      <details open className="rl-meta-section">
        <summary className="rl-meta-summary">Parameters</summary>
        <div className="rl-meta-body">
          <div className="rl-meta-actions">
            <span className="rl-hint">
              Bind values referenced as <code>:name</code> in SQL; the default applies
              when a caller omits the value.
            </span>
            <button
              type="button"
              className="rl-btn"
              onClick={() =>
                setParams({
                  ...params,
                  [uniqueKey(new Set(Object.keys(params)), "param")]: { type: "string" },
                })
              }
            >
              + Add param
            </button>
          </div>

          {paramEntries.length === 0 ? (
            <span className="rl-hint">No parameters yet.</span>
          ) : (
            <div className="rl-grid-scroll">
              <div className="rl-param-head">
                <span>Name</span>
                <span>Type</span>
                <span>Default</span>
                <span>Req</span>
                <span />
              </div>
              {paramEntries.map(([key, spec], i) => (
                <div key={i} className="rl-param-row">
                  <input
                    className="rl-meta-key"
                    value={key}
                    onChange={(e) => setParams(renameKey(params, i, e.target.value))}
                    placeholder="param_name"
                    aria-label="Param name"
                  />
                  <select
                    value={spec.type ?? "string"}
                    onChange={(e) => setParams(patchValue(params, i, { type: e.target.value as ParamType }))}
                    aria-label="Param type"
                  >
                    {PARAM_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                  <input
                    value={spec.default == null ? "" : String(spec.default)}
                    onChange={(e) => setParams(patchValue(params, i, { default: e.target.value || undefined }))}
                    placeholder="default"
                    aria-label="Param default"
                  />
                  <span className="rl-cell-center">
                    <input
                      type="checkbox"
                      checked={spec.required ?? false}
                      onChange={(e) => setParams(patchValue(params, i, { required: e.target.checked }))}
                      aria-label="Required"
                    />
                  </span>
                  <span className="rl-cell-center">
                    <button
                      type="button"
                      className="rl-btn rl-btn-sm"
                      onClick={() => setParams(removeAt(params, i))}
                      title="Remove param"
                    >
                      ✕
                    </button>
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </details>

      {/* -------------------- Chart -------------------- */}
      <details open className="rl-meta-section">
        <summary className="rl-meta-summary">Chart</summary>
        <div className="rl-meta-body">
          <label className="rl-hint">
            <input
              type="checkbox"
              checked={chart !== null}
              onChange={(e) =>
                e.target.checked
                  ? setChart({ type: "bar", x: pickerKeys[0] ?? "", y: [] })
                  : setChart(null)
              }
            />{" "}
            enable — pick chart type, x-axis, and one or more y-series measures.
          </label>
          {chart && (
            <div className="rl-chart-builder">
              <div className="rl-meta-row">
                <select
                  value={chart.type}
                  onChange={(e) => setChart({ type: e.target.value as ChartType })}
                  aria-label="Chart type"
                >
                  {CHART_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
                <label className="rl-hint">x-axis</label>
                <select value={chart.x} onChange={(e) => setChart({ x: e.target.value })} aria-label="Chart x">
                  <option value="">(x column)</option>
                  {pickerKeys.map((k) => (
                    <option key={k} value={k}>
                      {k}
                    </option>
                  ))}
                </select>
                <label className="rl-hint">agg</label>
                <select
                  value={chart.agg ?? "sum"}
                  onChange={(e) => setChart({ agg: e.target.value as "sum" | "avg" })}
                  aria-label="Chart aggregate"
                >
                  <option value="sum">sum</option>
                  <option value="avg">avg</option>
                </select>
              </div>
              <span className="rl-hint">y-series (measures)</span>
              <div className="rl-chart-y">
                {pickerKeys.length === 0 && (
                  <span className="rl-hint">Add columns or preview to pick y-series.</span>
                )}
                {pickerKeys.map((k) => (
                  <label key={k} className="rl-hint">
                    <input type="checkbox" checked={yList.includes(k)} onChange={() => toggleY(k)} /> {k}
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>
      </details>
    </div>
  );
}
