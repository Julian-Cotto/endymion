import type { ColumnConfig } from "../../types/reports";
import type { ColStat } from "./tableAnalysis";
import {
  aggregate,
  columnLabel,
  defaultAgg,
  formatAggregate,
  toNumber,
} from "./format";
import { Sparkline } from "./Sparkline";

type Row = Record<string, unknown>;

const MAX_MEASURES = 4;

/** A compact metrics strip above the table: distinct count of the identity
 * column plus auto-aggregates of the measure columns. Turns a raw grid into
 * something that reads like an analytics view. */
export function SummaryStrip({
  columns,
  columnConfig,
  rows,
  stats,
}: {
  columns: string[];
  columnConfig: Record<string, ColumnConfig>;
  rows: Row[];
  stats: Record<string, ColStat>;
}) {
  if (!rows.length) return null;

  const firstCol = columns[0];
  const measures = columns
    .filter((c) => stats[c]?.measure)
    .slice(0, MAX_MEASURES);

  if (!firstCol && !measures.length) return null;

  const tiles: Array<{ label: string; value: string; series?: number[] }> = [];

  if (firstCol) {
    tiles.push({
      label: columnLabel(firstCol, columnConfig[firstCol]),
      value: stats[firstCol]?.distinct.toLocaleString() ?? "—",
    });
  }

  for (const c of measures) {
    const kind = defaultAgg(columnConfig[c]);
    const series = rows
      .map((r) => r[c])
      .filter((v) => v !== null && v !== undefined && v !== "")
      .map(toNumber);
    const agg = aggregate(series, kind);
    tiles.push({
      label: `${columnLabel(c, columnConfig[c])} · ${kind}`,
      value: formatAggregate(agg, columnConfig[c]),
      series,
    });
  }

  return (
    <div className="rl-summary">
      {tiles.map((t, i) => (
        <div className="rl-summary-tile" key={i}>
          <div className="rl-summary-label">{t.label}</div>
          <div className="rl-summary-value">{t.value}</div>
          {t.series && t.series.length > 1 && (
            <div className="rl-summary-spark">
              <Sparkline values={t.series} />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
