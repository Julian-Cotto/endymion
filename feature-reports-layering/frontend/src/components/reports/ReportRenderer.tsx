import { useEffect, useMemo, useState } from "react";
import type { ChartConfig, ColumnConfig, ReportView } from "../../types/reports";
import { DataTable, type Drill } from "./DataTable";
import { ReportChart } from "./Charts";
import { KpiCards } from "./KpiCards";
import { SummaryStrip } from "./SummaryStrip";
import { analyzeColumns } from "./tableAnalysis";

/** The single consistent renderer every report flows through.
 * BAs only supply logic + metadata; look-and-feel lives here. */
export function ReportRenderer({ report }: { report: ReportView }) {
  const outputs = new Set(report.output_types);

  // Drill-through lives here so the summary AND the table reflect the same
  // filtered subset. Reset whenever the report changes.
  const [drill, setDrill] = useState<Drill[]>([]);
  useEffect(() => setDrill([]), [report.slug]);
  const addDrill = (col: string, value: unknown) => {
    const v = String(value);
    setDrill((cur) =>
      cur.some((d) => d.col === col && d.value === v) ? cur : [...cur, { col, value: v }],
    );
  };
  const drilledRows = useMemo(
    () =>
      drill.length === 0
        ? report.rows
        : report.rows.filter((r) => drill.every((d) => String(r[d.col] ?? "") === d.value)),
    [report.rows, drill],
  );
  const columns =
    report.result_columns.length > 0
      ? report.result_columns
      : Object.keys(report.columns);

  // The BA's metadata keys may not match the driver's column casing
  // (Snowflake here returns lowercase). Remap config + chart to the actual
  // result-column casing so labels/formats/charts line up regardless.
  const actualByLower = new Map(columns.map((c) => [c.toLowerCase(), c]));
  const actual = (key: string) => actualByLower.get(key.toLowerCase()) ?? key;

  const columnConfig: Record<string, ColumnConfig> = {};
  for (const [key, cfg] of Object.entries(report.columns)) {
    columnConfig[actual(key)] = cfg;
  }

  const chart: ChartConfig | null = report.chart
    ? {
        ...report.chart,
        x: actual(report.chart.x),
        y: Array.isArray(report.chart.y)
          ? report.chart.y.map(actual)
          : actual(report.chart.y),
      }
    : null;

  const normalizeChart = (c: ChartConfig): ChartConfig => ({
    ...c,
    x: actual(c.x),
    y: Array.isArray(c.y) ? c.y.map(actual) : actual(c.y),
  });

  const visible = columns.filter((c) => !columnConfig[c]?.hidden);
  // Stats + summaries recompute on the drilled subset so KPIs, bars and
  // sparklines all reflect the active drill-through filter.
  const stats = analyzeColumns(visible, drilledRows, columnConfig, visible[0]);

  const summary = (
    <SummaryStrip
      columns={visible}
      columnConfig={columnConfig}
      rows={drilledRows}
      stats={stats}
    />
  );
  const table = (
    <DataTable
      key={report.slug}
      viewKey={report.slug}
      columns={columns}
      columnConfig={columnConfig}
      rows={drilledRows}
      stats={stats}
      drill={drill}
      onDrill={addDrill}
      onRemoveDrill={(i) => setDrill((cur) => cur.filter((_, idx) => idx !== i))}
      onClearDrill={() => setDrill([])}
    />
  );

  // ---- Layout mode: compose blocks in a 12-column grid ----
  if (report.layout && report.layout.length > 0) {
    return (
      <div className="rl-layout">
        {report.layout.map((block, i) => {
          const span = Math.min(12, Math.max(1, block.span ?? 12));
          return (
            <div
              className="rl-layout-block"
              style={{ gridColumn: `span ${span}` }}
              key={i}
            >
              {block.title && block.type !== "note" && (
                <h4 className="rl-block-title">{block.title}</h4>
              )}
              {block.type === "kpi" && summary}
              {block.type === "table" && table}
              {block.type === "chart" && block.chart && (
                <div className="rl-card rl-chart-card">
                  <ReportChart chart={normalizeChart(block.chart)} rows={drilledRows} />
                </div>
              )}
              {block.type === "note" && (
                <div className="rl-note">
                  {block.title && <strong>{block.title}</strong>}
                  {block.text && <p>{block.text}</p>}
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  }

  // ---- Legacy stacked mode (output_types) ----
  const showKpi = outputs.has("kpi");
  const showChart = outputs.has("chart") && chart;
  const showTable = outputs.has("table") || (!showKpi && !showChart);

  return (
    <div>
      {showKpi && (
        <KpiCards
          columns={columns}
          columnConfig={columnConfig}
          rows={drilledRows}
          chart={chart}
        />
      )}

      {showChart && chart && (
        <section className="rl-section">
          <h4>Chart</h4>
          <ReportChart chart={chart} rows={drilledRows} />
        </section>
      )}

      {showTable && (
        <>
          {summary}
          {table}
        </>
      )}
    </div>
  );
}
