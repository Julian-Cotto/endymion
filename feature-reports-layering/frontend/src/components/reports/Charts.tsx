import { useRef, useState } from "react";
import type { ChartConfig } from "../../types/reports";
import { toNumber } from "./format";

type Row = Record<string, unknown>;

// Categorical palette — validated (CVD ΔE 33.7; passes dark, light relief = legend+table).
const PALETTE = ["#2f6bff", "#1f9d63", "#c9821a", "#8b5cf6", "#d4483b", "#0ea5b7"];

function yKeys(chart: ChartConfig): string[] {
  return Array.isArray(chart.y) ? chart.y : [chart.y];
}

function fmt(v: number): string {
  const a = Math.abs(v);
  if (a >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (a >= 1_000) return `${(v / 1_000).toFixed(1)}k`;
  return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

interface Tip {
  x: number;
  y: number;
  title: string;
  rows: Array<{ color?: string; label: string; value: string }>;
}

export function ReportChart({ chart, rows }: { chart: ChartConfig; rows: Row[] }) {
  if (!rows.length) return <p className="rl-empty">No data to chart.</p>;
  if (chart.type === "pie") return <PieChart chart={chart} rows={rows} />;
  return <CartesianChart chart={chart} rows={rows} />;
}

function Legend({ items }: { items: string[] }) {
  if (items.length < 2) return null;
  return (
    <div className="rl-chart-legend">
      {items.map((label, i) => (
        <span key={label}>
          <span className="rl-legend-dot" style={{ background: PALETTE[i % PALETTE.length] }} />
          {label}
        </span>
      ))}
    </div>
  );
}

function Tooltip({ tip }: { tip: Tip | null }) {
  if (!tip) return null;
  return (
    <div
      className="rl-chart-tip"
      style={{ left: tip.x, top: tip.y }}
      role="tooltip"
      aria-hidden
    >
      <div className="rl-chart-tip-title">{tip.title}</div>
      {tip.rows.map((r, i) => (
        <div className="rl-chart-tip-row" key={i}>
          {r.color && <span className="rl-legend-dot" style={{ background: r.color }} />}
          <span className="rl-chart-tip-label">{r.label}</span>
          <span className="rl-chart-tip-value">{r.value}</span>
        </div>
      ))}
    </div>
  );
}

/** Bar / line / area share axes + scale, with a shared crosshair tooltip. */
function CartesianChart({ chart, rows }: { chart: ChartConfig; rows: Row[] }) {
  const W = 720;
  const H = 320;
  const pad = { top: 16, right: 16, bottom: 44, left: 56 };
  const plotW = W - pad.left - pad.right;
  const plotH = H - pad.top - pad.bottom;

  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [hover, setHover] = useState<number | null>(null);
  const [tip, setTip] = useState<Tip | null>(null);

  const series = yKeys(chart);

  // Aggregate rows sharing an x value so detail data (e.g. 812 store-days)
  // charts as a readable series (e.g. one bar per day). Order = first-seen.
  const order: string[] = [];
  const acc = new Map<string, Record<string, number[]>>();
  for (const r of rows) {
    const k = String(r[chart.x] ?? "");
    if (!acc.has(k)) {
      acc.set(k, {});
      order.push(k);
    }
    const rec = acc.get(k)!;
    for (const key of series) (rec[key] ??= []).push(toNumber(r[key]));
  }
  const combine =
    chart.agg === "avg"
      ? (a: number[]) => a.reduce((s, v) => s + v, 0) / (a.length || 1)
      : (a: number[]) => a.reduce((s, v) => s + v, 0);
  const data = order.map((k) => ({
    label: k,
    values: Object.fromEntries(series.map((key) => [key, combine(acc.get(k)![key] ?? [0])])),
  }));
  const n = data.length;

  const labels = data.map((d) => d.label);
  const maxVal =
    Math.max(1, ...data.flatMap((d) => series.map((k) => d.values[k]))) * 1.1;

  const x = (i: number) => pad.left + (plotW * (i + 0.5)) / n;
  const y = (v: number) => pad.top + plotH * (1 - v / maxVal);

  const ticks = 4;
  const gridVals = Array.from({ length: ticks + 1 }, (_, i) => (maxVal * i) / ticks);

  const isBar = chart.type === "bar";
  const bandW = plotW / n;
  const barW = Math.max(2, (bandW * 0.7) / series.length);

  function onMove(e: React.MouseEvent) {
    const wrap = wrapRef.current;
    if (!wrap) return;
    const rect = wrap.getBoundingClientRect();
    const vbX = ((e.clientX - rect.left) / rect.width) * W;
    let i = Math.round(((vbX - pad.left) / plotW) * n - 0.5);
    i = Math.max(0, Math.min(n - 1, i));
    setHover(i);
    setTip({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      title: labels[i],
      rows: series.map((k, si) => ({
        color: PALETTE[si % PALETTE.length],
        label: k,
        value: fmt(data[i].values[k]),
      })),
    });
  }
  function onLeave() {
    setHover(null);
    setTip(null);
  }

  return (
    <div className="rl-chart-wrap" ref={wrapRef}>
      <svg
        className="rl-chart"
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="xMidYMid meet"
        role="img"
        onMouseMove={onMove}
        onMouseLeave={onLeave}
      >
        {gridVals.map((v, i) => (
          <g key={i}>
            <line
              className="rl-axis"
              x1={pad.left}
              x2={W - pad.right}
              y1={y(v)}
              y2={y(v)}
              opacity={i === 0 ? 1 : 0.5}
            />
            <text className="rl-tick" x={pad.left - 8} y={y(v) + 4} textAnchor="end">
              {fmt(v)}
            </text>
          </g>
        ))}

        {/* crosshair */}
        {hover !== null && (
          <line
            className="rl-crosshair"
            x1={x(hover)}
            x2={x(hover)}
            y1={pad.top}
            y2={pad.top + plotH}
          />
        )}

        {series.map((key, si) => {
          const color = PALETTE[si % PALETTE.length];
          if (isBar) {
            return data.map((d, i) => {
              const v = d.values[key];
              const bx = x(i) - (barW * series.length) / 2 + si * barW;
              return (
                <rect
                  key={`${key}-${i}`}
                  className="rl-bar"
                  x={bx}
                  y={y(v)}
                  width={Math.max(1, barW - 1)}
                  height={Math.max(0, pad.top + plotH - y(v))}
                  rx={2}
                  fill={color}
                  opacity={hover === null || hover === i ? 1 : 0.4}
                />
              );
            });
          }
          const pts = data.map((d, i) => `${x(i)},${y(d.values[key])}`).join(" ");
          const area = `${pad.left},${pad.top + plotH} ${pts} ${W - pad.right},${pad.top + plotH}`;
          return (
            <g key={key}>
              {chart.type === "area" && <polygon points={area} fill={color} opacity={0.12} />}
              <polyline
                points={pts}
                fill="none"
                stroke={color}
                strokeWidth={2}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              {hover !== null && (
                <circle cx={x(hover)} cy={y(data[hover].values[key])} r={4} fill={color}
                  stroke="var(--rl-surface)" strokeWidth={2} />
              )}
            </g>
          );
        })}

        {labels.map((label, i) => {
          const step = Math.ceil(n / 8);
          if (i % step !== 0) return null;
          return (
            <text key={i} className="rl-tick" x={x(i)} y={H - pad.bottom + 18} textAnchor="middle">
              {label.length > 12 ? `${label.slice(0, 11)}…` : label}
            </text>
          );
        })}
      </svg>
      <Tooltip tip={tip} />
      <Legend items={series} />
    </div>
  );
}

const PIE_MAX = 6; // cap slices; remainder folds into "Other"

function PieChart({ chart, rows }: { chart: ChartConfig; rows: Row[] }) {
  const key = yKeys(chart)[0];
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [tip, setTip] = useState<Tip | null>(null);

  // Aggregate + cap so a pie never renders hundreds of unreadable slivers.
  const agg = new Map<string, number>();
  for (const r of rows) {
    const k = String(r[chart.x] ?? "—");
    agg.set(k, (agg.get(k) ?? 0) + toNumber(r[key]));
  }
  let entries = [...agg.entries()].sort((a, b) => b[1] - a[1]);
  if (entries.length > PIE_MAX) {
    const head = entries.slice(0, PIE_MAX - 1);
    const other = entries.slice(PIE_MAX - 1).reduce((s, [, v]) => s + v, 0);
    entries = [...head, ["Other", other]];
  }
  const total = entries.reduce((s, [, v]) => s + v, 0) || 1;

  const R = 120;
  const cx = 160;
  const cy = 160;
  let angle = -Math.PI / 2;
  const slices = entries.map(([label, value], i) => {
    const frac = value / total;
    const start = angle;
    const end = angle + frac * Math.PI * 2;
    angle = end;
    const large = end - start > Math.PI ? 1 : 0;
    const path = `M ${cx} ${cy} L ${cx + R * Math.cos(start)} ${cy + R * Math.sin(start)} A ${R} ${R} 0 ${large} 1 ${cx + R * Math.cos(end)} ${cy + R * Math.sin(end)} Z`;
    return { label, value, frac, path, color: PALETTE[i % PALETTE.length] };
  });

  function showTip(e: React.MouseEvent, s: (typeof slices)[number]) {
    const rect = wrapRef.current?.getBoundingClientRect();
    if (!rect) return;
    setTip({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      title: s.label,
      rows: [{ color: s.color, label: fmt(s.value), value: `${(s.frac * 100).toFixed(1)}%` }],
    });
  }

  return (
    <div className="rl-chart-wrap" ref={wrapRef}>
      <svg
        className="rl-chart"
        viewBox="0 0 320 320"
        preserveAspectRatio="xMidYMid meet"
        role="img"
        style={{ maxWidth: 360, margin: "0 auto" }}
        onMouseLeave={() => setTip(null)}
      >
        {slices.map((s, i) => (
          <path
            key={i}
            d={s.path}
            fill={s.color}
            stroke="var(--rl-surface)"
            strokeWidth={2}
            onMouseMove={(e) => showTip(e, s)}
          />
        ))}
      </svg>
      <Tooltip tip={tip} />
      <Legend items={slices.map((s) => s.label)} />
    </div>
  );
}
