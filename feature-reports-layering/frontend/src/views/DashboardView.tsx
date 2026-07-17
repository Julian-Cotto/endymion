import { useEffect, useState } from "react";
import { getReport, listReports } from "../services/reportsApi";
import type { ReportView, ReportSummary } from "../types/reports";
import { navigate } from "../hooks/useHashRoute";
import { relativeTime } from "../utils/time";
import { analyzeColumns } from "../components/reports/tableAnalysis";
import {
  aggregate,
  columnLabel,
  defaultAgg,
  formatAggregate,
  toNumber,
} from "../components/reports/format";
import { Sparkline } from "../components/reports/Sparkline";
import { CardGridSkeleton } from "../components/reports/Skeletons";
import { EmptyState } from "../components/reports/EmptyState";

interface Metric {
  label: string;
  value: string;
  series: number[];
}

interface Panel {
  summary: ReportSummary;
  view?: ReportView;
  metrics: Metric[];
}

const MAX_METRICS = 3;

function buildMetrics(view: ReportView): Metric[] {
  const cols =
    view.result_columns.length > 0 ? view.result_columns : Object.keys(view.columns);
  const stats = analyzeColumns(cols, view.rows, view.columns, cols[0]);
  const measures = cols.filter((c) => stats[c]?.measure).slice(0, MAX_METRICS);
  return measures.map((c) => {
    const series = view.rows
      .map((r) => r[c])
      .filter((v) => v !== null && v !== undefined && v !== "")
      .map(toNumber);
    const kind = defaultAgg(view.columns[c]);
    return {
      label: `${columnLabel(c, view.columns[c])} · ${kind}`,
      value: formatAggregate(aggregate(series, kind), view.columns[c]),
      series,
    };
  });
}

export function DashboardView() {
  const [panels, setPanels] = useState<Panel[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const reports = await listReports();
        const built = await Promise.all(
          reports.map(async (summary): Promise<Panel> => {
            try {
              const view = await getReport(summary.slug);
              return { summary, view, metrics: buildMetrics(view) };
            } catch {
              return { summary, metrics: [] };
            }
          }),
        );
        if (alive) setPanels(built);
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : "Failed to load");
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  if (error) return <p className="rl-error">Failed to load dashboard: {error}</p>;
  if (!panels) return <CardGridSkeleton count={4} />;
  if (panels.length === 0) {
    return <EmptyState title="No reports to show yet" hint="Published reports appear here as live metric panels." />;
  }

  return (
    <div className="rl-dash">
      {panels.map((p) => (
        <button
          key={p.summary.slug}
          className="rl-card rl-dash-panel"
          onClick={() => navigate({ view: "report", slug: p.summary.slug })}
        >
          <div className="rl-dash-head">
            <h3>{p.summary.title}</h3>
            <span
              className="rl-status-dot"
              data-state={
                p.summary.last_snapshot_status === "error"
                  ? "error"
                  : p.summary.last_snapshot_at
                    ? "ok"
                    : "none"
              }
            />
          </div>
          <div className="rl-dash-sub">
            {p.view ? `${p.view.row_count.toLocaleString()} rows` : "—"} ·{" "}
            {p.summary.last_snapshot_at
              ? `updated ${relativeTime(p.summary.last_snapshot_at)}`
              : "no data yet"}
          </div>
          <div className="rl-dash-metrics">
            {p.metrics.length === 0 && (
              <span className="rl-hint">No numeric measures to summarize.</span>
            )}
            {p.metrics.map((m, i) => (
              <div className="rl-dash-metric" key={i}>
                <div className="rl-dash-metric-label">{m.label}</div>
                <div className="rl-dash-metric-value">{m.value}</div>
                <Sparkline values={m.series} width={110} height={26} />
              </div>
            ))}
          </div>
        </button>
      ))}
    </div>
  );
}
