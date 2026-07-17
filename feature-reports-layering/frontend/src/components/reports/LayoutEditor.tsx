import { useState } from "react";
import type {
  BlockType,
  ChartType,
  LayoutBlock,
} from "../../types/reports";
import { ReportChart } from "./Charts";

type Row = Record<string, unknown>;

const BLOCK_TYPES: BlockType[] = ["kpi", "chart", "table", "note"];
const CHART_TYPES: ChartType[] = ["bar", "line", "area", "pie"];
const SPANS = [3, 4, 6, 8, 9, 12];

function spanLabel(s: number): string {
  return (
    { 3: "¼", 4: "⅓", 6: "½", 8: "⅔", 9: "¾", 12: "Full" }[s] ?? `${s}/12`
  );
}
const clampSpan = (s?: number) => Math.min(12, Math.max(1, s ?? 12));

function defaultBlock(type: BlockType): LayoutBlock {
  if (type === "chart")
    return { type, span: 6, title: "", chart: { type: "bar", x: "", y: "", agg: "sum" } };
  if (type === "note") return { type, span: 12, title: "", text: "" };
  return { type, span: 12 };
}

function ColField({
  label,
  value,
  columns,
  onChange,
}: {
  label: string;
  value: string;
  columns: string[];
  onChange: (v: string) => void;
}) {
  return (
    <label className="rl-le-field">
      {label}
      {columns.length > 0 ? (
        <select value={value} onChange={(e) => onChange(e.target.value)}>
          <option value="">—</option>
          {columns.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      ) : (
        <input value={value} onChange={(e) => onChange(e.target.value)} placeholder="column" />
      )}
    </label>
  );
}

/** Multi-series Y selection via toggle chips (single-select for pie). */
function YPicker({
  value,
  columns,
  pie,
  onChange,
}: {
  value: string | string[] | undefined;
  columns: string[];
  pie: boolean;
  onChange: (y: string | string[]) => void;
}) {
  const selected = Array.isArray(value) ? value : value ? [value] : [];
  function toggle(c: string) {
    if (pie) {
      onChange(c);
      return;
    }
    const next = selected.includes(c)
      ? selected.filter((x) => x !== c)
      : [...selected, c];
    onChange(next);
  }
  return (
    <div className="rl-le-yfield">
      <span className="rl-le-field" style={{ alignSelf: "center" }}>
        {pie ? "Value" : "Y (one+)"}
      </span>
      <div className="rl-le-chips">
        {columns.length === 0 && <span className="rl-hint">define columns first</span>}
        {columns.map((c) => (
          <button
            type="button"
            key={c}
            className={`rl-le-chip${selected.includes(c) ? " is-on" : ""}`}
            onClick={() => toggle(c)}
          >
            {c}
          </button>
        ))}
      </div>
    </div>
  );
}

/** Inline live preview of a chart block using sample rows. */
function ChartPreview({ block, rows }: { block: LayoutBlock; rows: Row[] }) {
  const c = block.chart;
  const ys = Array.isArray(c?.y) ? c?.y : c?.y ? [c.y] : [];
  if (!c?.x || ys.length === 0) {
    return <div className="rl-le-preview-hint">Pick an X and at least one Y to preview.</div>;
  }
  if (rows.length === 0) {
    return <div className="rl-le-preview-hint">Preview appears once columns are defined.</div>;
  }
  return (
    <div className="rl-le-chart-preview">
      <ReportChart chart={c} rows={rows} />
    </div>
  );
}

/** Visual editor for a report's block layout. Drag to reorder, pick each
 * block's type / width, and configure chart fields — no JSON by hand. */
export function LayoutEditor({
  value,
  onChange,
  columns,
  previewRows = [],
}: {
  value: LayoutBlock[];
  onChange: (blocks: LayoutBlock[]) => void;
  columns: string[];
  previewRows?: Row[]; // sample rows so chart blocks preview live
}) {
  const [dragIdx, setDragIdx] = useState<number | null>(null);

  const patch = (i: number, p: Partial<LayoutBlock>) =>
    onChange(value.map((b, idx) => (idx === i ? { ...b, ...p } : b)));
  const patchChart = (i: number, p: Record<string, unknown>) =>
    onChange(
      value.map((b, idx) =>
        idx === i
          ? { ...b, chart: { type: "bar", x: "", y: "", ...(b.chart ?? {}), ...p } }
          : b,
      ),
    );
  const move = (from: number, to: number) => {
    if (to < 0 || to >= value.length) return;
    const arr = [...value];
    const [m] = arr.splice(from, 1);
    arr.splice(to, 0, m);
    onChange(arr);
  };

  return (
    <div className="rl-le">
      {/* live grid preview */}
      <div className="rl-le-preview">
        {value.length === 0 && (
          <span className="rl-hint">No blocks yet — add one below.</span>
        )}
        {value.map((b, i) => (
          <div
            key={i}
            className={`rl-le-pv rl-le-pv-${b.type}`}
            style={{ gridColumn: `span ${clampSpan(b.span)}` }}
          >
            {b.type}
            {b.title ? `: ${b.title}` : ""}
          </div>
        ))}
      </div>

      {/* block editors */}
      {value.map((b, i) => (
        <div
          key={i}
          className={`rl-le-block${dragIdx === i ? " is-dragging" : ""}`}
          draggable
          onDragStart={() => setDragIdx(i)}
          onDragEnd={() => setDragIdx(null)}
          onDragOver={(e) => e.preventDefault()}
          onDrop={() => {
            if (dragIdx !== null && dragIdx !== i) move(dragIdx, i);
            setDragIdx(null);
          }}
        >
          <span className="rl-le-handle" title="Drag to reorder">
            ⠿
          </span>

          <select
            className="rl-le-type"
            value={b.type}
            onChange={(e) => {
              const type = e.target.value as BlockType;
              patch(i, {
                type,
                ...(type === "chart" && !b.chart
                  ? { chart: { type: "bar", x: "", y: "", agg: "sum" } }
                  : {}),
              });
            }}
          >
            {BLOCK_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>

          <label className="rl-le-field">
            Width
            <select value={clampSpan(b.span)} onChange={(e) => patch(i, { span: Number(e.target.value) })}>
              {SPANS.map((s) => (
                <option key={s} value={s}>
                  {spanLabel(s)}
                </option>
              ))}
            </select>
          </label>

          {(b.type === "chart" || b.type === "note") && (
            <input
              className="rl-le-title"
              placeholder="Title"
              value={b.title ?? ""}
              onChange={(e) => patch(i, { title: e.target.value })}
            />
          )}

          {b.type === "chart" && (
            <>
              <label className="rl-le-field">
                Type
                <select value={b.chart?.type ?? "bar"} onChange={(e) => patchChart(i, { type: e.target.value })}>
                  {CHART_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </label>
              <ColField
                label="X"
                value={b.chart?.x ?? ""}
                columns={columns}
                onChange={(v) => patchChart(i, { x: v })}
              />
              <label className="rl-le-field">
                Agg
                <select value={b.chart?.agg ?? "sum"} onChange={(e) => patchChart(i, { agg: e.target.value })}>
                  <option value="sum">sum</option>
                  <option value="avg">avg</option>
                </select>
              </label>
              <YPicker
                value={b.chart?.y}
                columns={columns}
                pie={b.chart?.type === "pie"}
                onChange={(y) => patchChart(i, { y })}
              />
              <ChartPreview block={b} rows={previewRows} />
            </>
          )}

          {b.type === "note" && (
            <input
              className="rl-le-title"
              placeholder="Note text"
              value={b.text ?? ""}
              onChange={(e) => patch(i, { text: e.target.value })}
            />
          )}

          <div className="rl-le-block-actions">
            <button type="button" onClick={() => move(i, i - 1)} disabled={i === 0} aria-label="Move up">
              ↑
            </button>
            <button
              type="button"
              onClick={() => move(i, i + 1)}
              disabled={i === value.length - 1}
              aria-label="Move down"
            >
              ↓
            </button>
            <button
              type="button"
              className="rl-le-remove"
              onClick={() => onChange(value.filter((_, idx) => idx !== i))}
              aria-label="Remove block"
            >
              ✕
            </button>
          </div>
        </div>
      ))}

      <div className="rl-le-add">
        <span className="rl-hint">Add block:</span>
        {BLOCK_TYPES.map((t) => (
          <button key={t} type="button" className="rl-btn" onClick={() => onChange([...value, defaultBlock(t)])}>
            + {t}
          </button>
        ))}
      </div>
    </div>
  );
}
