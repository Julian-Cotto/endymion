import type { ChartConfig, ColumnConfig } from "../../types/reports";
import { columnLabel, formatValue, isNumericFormat, toNumber } from "./format";

type Row = Record<string, unknown>;

/** KPI tiles: one big number per numeric column.
 * Single-row snapshot -> show its values directly.
 * Multi-row -> show the sum of each numeric column. */
export function KpiCards({
  columns,
  columnConfig,
  rows,
  chart,
}: {
  columns: string[];
  columnConfig: Record<string, ColumnConfig>;
  rows: Row[];
  chart: ChartConfig | null;
}) {
  if (!rows.length) return null;

  const numericCols = columns.filter(
    (c) => !columnConfig[c]?.hidden && isNumericFormat(columnConfig[c]?.format),
  );
  const cols = numericCols.length
    ? numericCols
    : chart
      ? (Array.isArray(chart.y) ? chart.y : [chart.y])
      : [];
  if (!cols.length) return null;

  const single = rows.length === 1;

  return (
    <div className="rl-kpis">
      {cols.map((c) => {
        const value = single
          ? rows[0][c]
          : rows.reduce((s, r) => s + toNumber(r[c]), 0);
        return (
          <div className="rl-kpi" key={c}>
            <div className="rl-kpi-label">
              {columnLabel(c, columnConfig[c])}
              {!single ? " (total)" : ""}
            </div>
            <div className="rl-kpi-value">
              {formatValue(value, columnConfig[c])}
            </div>
          </div>
        );
      })}
    </div>
  );
}
