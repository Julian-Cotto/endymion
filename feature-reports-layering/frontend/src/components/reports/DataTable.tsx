import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import type { ColumnConfig } from "../../types/reports";
import {
  aggregate,
  columnLabel,
  defaultAgg,
  formatValue,
  looksNumeric,
  toNumber,
} from "./format";
import {
  analyzeColumns,
  badgeStyle,
  barStyle,
  heatBackground,
  type ColStat,
} from "./tableAnalysis";
import { RowDrawer } from "./RowDrawer";
import { useMediaQuery } from "../../hooks/useMediaQuery";

type Row = Record<string, unknown>;
export type Drill = { col: string; value: string };

const FROZEN = 2; // freeze the first two (identity) columns

interface SavedPrefs {
  compact?: boolean;
  groupBy?: string;
  hidden?: string[];
  sortKey?: string | null;
  asc?: boolean;
}

function loadPrefs(key: string | undefined): SavedPrefs {
  if (!key) return {};
  try {
    return JSON.parse(localStorage.getItem(`rl:view:${key}`) ?? "{}");
  } catch {
    return {};
  }
}

export function DataTable({
  columns,
  columnConfig,
  rows,
  stats,
  viewKey,
  drill = [],
  onDrill,
  onRemoveDrill,
  onClearDrill,
}: {
  columns: string[];
  columnConfig: Record<string, ColumnConfig>;
  rows: Row[];
  stats?: Record<string, ColStat>;
  viewKey?: string; // report slug — persists the view controls per report
  drill?: Drill[];
  onDrill?: (col: string, value: unknown) => void;
  onRemoveDrill?: (index: number) => void;
  onClearDrill?: () => void;
}) {
  const allCols = columns.filter((c) => !columnConfig[c]?.hidden);

  const saved = useMemo(() => loadPrefs(viewKey), [viewKey]);
  const [sortKey, setSortKey] = useState<string | null>(saved.sortKey ?? null);
  const [asc, setAsc] = useState(saved.asc ?? true);
  const [filter, setFilter] = useState("");
  const [compact, setCompact] = useState(saved.compact ?? false);
  const [hiddenCols, setHiddenCols] = useState<Set<string>>(new Set(saved.hidden ?? []));
  const [showColsPanel, setShowColsPanel] = useState(false);
  const [groupBy, setGroupBy] = useState(saved.groupBy ?? "");
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [detailRow, setDetailRow] = useState<Row | null>(null);
  const [cardLimit, setCardLimit] = useState(60); // mobile "load more" window

  // Reset the mobile window when the visible set changes.
  useEffect(() => {
    setCardLimit(60);
  }, [filter, groupBy, sortKey, asc, drill, rows]);

  // Infinite scroll: bump the window when the sentinel scrolls into view.
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  // Persist the durable view controls (not transient filter/drill/detail).
  useEffect(() => {
    if (!viewKey) return;
    const prefs: SavedPrefs = {
      compact,
      groupBy,
      hidden: [...hiddenCols],
      sortKey,
      asc,
    };
    try {
      localStorage.setItem(`rl:view:${viewKey}`, JSON.stringify(prefs));
    } catch {
      /* storage unavailable — ignore */
    }
  }, [viewKey, compact, groupBy, hiddenCols, sortKey, asc]);

  const visible = allCols.filter((c) => !hiddenCols.has(c));
  const firstCol = visible[0];
  const isMobile = useMediaQuery("(max-width: 720px)");

  const colStats = useMemo(
    () => stats ?? analyzeColumns(visible, rows, columnConfig, firstCol),
    [stats, visible, rows, columnConfig, firstCol],
  );

  const numericByCol = useMemo(() => {
    const map: Record<string, boolean> = {};
    for (const c of visible) {
      map[c] =
        colStats[c]?.numeric ??
        looksNumeric(columnConfig[c]?.format, rows.map((r) => r[c]));
    }
    return map;
  }, [visible, columnConfig, rows, colStats]);

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) =>
      visible.some((c) => String(r[c] ?? "").toLowerCase().includes(q)),
    );
  }, [rows, filter, visible]);

  const sorted = useMemo(() => {
    if (!sortKey) return filtered;
    const numeric = numericByCol[sortKey];
    return [...filtered].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      const cmp = numeric
        ? toNumber(av) - toNumber(bv)
        : String(av ?? "").localeCompare(String(bv ?? ""), undefined, { numeric: true });
      return asc ? cmp : -cmp;
    });
  }, [filtered, sortKey, asc, numericByCol]);

  const canWindow = isMobile && !groupBy && sorted.length > cardLimit;
  useEffect(() => {
    if (!canWindow || typeof IntersectionObserver === "undefined") return;
    const el = sentinelRef.current;
    if (!el) return;
    const io = new IntersectionObserver((entries) => {
      if (entries[0]?.isIntersecting) setCardLimit((n) => n + 60);
    });
    io.observe(el);
    return () => io.disconnect();
  }, [canWindow]);

  // Column-group bands (metadata-driven).
  const bands = useMemo(() => {
    const out: Array<{ label: string; span: number }> = [];
    for (const c of visible) {
      const g = columnConfig[c]?.group ?? "";
      const last = out[out.length - 1];
      if (last && last.label === g) last.span++;
      else out.push({ label: g, span: 1 });
    }
    return out;
  }, [visible, columnConfig]);
  const hasBands = bands.some((b) => b.label);

  // Measure first column width so the 2nd frozen column can offset correctly.
  const headRef = useRef<HTMLTableRowElement>(null);
  const [col0w, setCol0w] = useState(0);
  useLayoutEffect(() => {
    const th = headRef.current?.children?.[0] as HTMLElement | undefined;
    if (th) setCol0w(th.offsetWidth);
  }, [visible, compact, sorted, groupBy]);

  const stickyStyle = (i: number): CSSProperties => {
    if (i === 0) return { left: 0 };
    if (i === 1) return { left: col0w };
    return {};
  };
  const stickyClass = (i: number) =>
    i < FROZEN ? (i === FROZEN - 1 ? "rl-sticky-col rl-sticky-edge" : "rl-sticky-col") : "";

  function onSort(key: string) {
    if (sortKey === key) setAsc((v) => !v);
    else {
      setSortKey(key);
      setAsc(true);
    }
  }
  function toggleCol(c: string) {
    setHiddenCols((cur) => {
      const next = new Set(cur);
      next.has(c) ? next.delete(c) : next.add(c);
      return next;
    });
  }
  function toggleGroup(key: string) {
    setCollapsed((cur) => {
      const next = new Set(cur);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  }

  const subtotal = (groupRows: Row[], c: string): string => {
    if (!colStats[c]?.measure) return "";
    const vals = groupRows
      .map((r) => r[c])
      .filter((v) => v !== null && v !== undefined && v !== "")
      .map(toNumber);
    return formatValue(aggregate(vals, defaultAgg(columnConfig[c])), columnConfig[c]);
  };

  function cell(c: string, i: number, row: Row) {
    const stat = colStats[c];
    const cfg = columnConfig[c];
    const raw = row[c];
    const isFirst = i === 0;
    const cls = [numericByCol[c] ? "rl-num" : "", stickyClass(i)].filter(Boolean).join(" ");
    const sticky = i < FROZEN ? stickyStyle(i) : {};

    const drillHere = (e: React.MouseEvent) => {
      e.stopPropagation(); // don't also open the row drawer
      onDrill?.(c, raw);
    };
    const canDrill = !!onDrill;
    const hasValue = raw !== null && raw !== undefined && raw !== "";

    // Badges drill on click.
    if (stat?.badge && !isFirst && hasValue) {
      return (
        <td key={c} className={cls || undefined} style={sticky}>
          <span
            className={`rl-badge${canDrill ? " rl-drillable" : ""}`}
            style={badgeStyle(raw)}
            onClick={canDrill ? drillHere : undefined}
            title={canDrill ? `Filter to ${formatValue(raw, cfg)}` : undefined}
          >
            {formatValue(raw, cfg)}
          </span>
        </td>
      );
    }

    // Identity (first) column drills on its value.
    if (isFirst && hasValue && canDrill) {
      return (
        <td key={c} className={cls || undefined} style={sticky}>
          <span className="rl-drill-link" onClick={drillHere} title="Filter to this">
            {formatValue(raw, cfg)}
          </span>
        </td>
      );
    }

    const heat = !isFirst ? heatBackground(raw, stat, cfg?.heat) : undefined;
    const vis = heat
      ? { background: heat }
      : !isFirst && !cfg?.heat && stat
        ? barStyle(raw, stat)
        : undefined;
    return (
      <td key={c} className={cls || undefined} style={{ ...sticky, ...vis }}>
        {formatValue(raw, cfg)}
      </td>
    );
  }

  const groups = useMemo(() => {
    if (!groupBy) return null;
    const map = new Map<string, Row[]>();
    for (const r of sorted) {
      const k = String(r[groupBy] ?? "—");
      (map.get(k) ?? map.set(k, []).get(k)!).push(r);
    }
    return [...map.entries()];
  }, [sorted, groupBy]);

  if (rows.length === 0) return <p className="rl-empty">No rows in this snapshot.</p>;

  const colCount = visible.length;

  // --- Mobile card layout: identity + badges + measures; tap for full detail.
  const secondCol =
    visible[1] && !colStats[visible[1]]?.measure && !colStats[visible[1]]?.badge
      ? visible[1]
      : undefined;
  const badgeCols = visible.filter((c) => c !== firstCol && colStats[c]?.badge);
  const measureCols = visible.filter((c) => colStats[c]?.measure);

  function renderCard(row: Row, key: number) {
    return (
      <div className="rl-mcard rl-data-row" key={key} onClick={() => setDetailRow(row)}>
        <div className="rl-mcard-head">
          <span className="rl-mcard-title">{formatValue(row[firstCol], columnConfig[firstCol])}</span>
          {secondCol && (
            <span className="rl-mcard-sub">{formatValue(row[secondCol], columnConfig[secondCol])}</span>
          )}
        </div>
        {badgeCols.length > 0 && (
          <div className="rl-mcard-badges">
            {badgeCols.map((c) => {
              const raw = row[c];
              if (raw === null || raw === undefined || raw === "") return null;
              return (
                <span
                  key={c}
                  className={`rl-badge${onDrill ? " rl-drillable" : ""}`}
                  style={badgeStyle(raw)}
                  onClick={
                    onDrill
                      ? (e) => {
                          e.stopPropagation();
                          onDrill(c, raw);
                        }
                      : undefined
                  }
                >
                  {formatValue(raw, columnConfig[c])}
                </span>
              );
            })}
          </div>
        )}
        {measureCols.length > 0 && (
          <div className="rl-mcard-metrics">
            {measureCols.map((c) => (
              <div className="rl-mcard-metric" key={c}>
                <span className="rl-mcard-metric-label">
                  {columnLabel(c, columnConfig[c])}
                </span>
                <span className="rl-mcard-metric-value" style={barStyle(row[c], colStats[c]) ?? {}}>
                  {formatValue(row[c], columnConfig[c])}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  if (isMobile) {
    return (
      <div>
        <div className="rl-toolbar rl-toolbar-mobile rl-no-print">
          <input
            className="rl-toolbar-search"
            type="search"
            placeholder="Filter…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
          <label className="rl-toolbar-group">
            Group
            <select value={groupBy} onChange={(e) => setGroupBy(e.target.value)}>
              <option value="">None</option>
              {visible.map((c) => (
                <option key={c} value={c}>
                  {columnLabel(c, columnConfig[c])}
                </option>
              ))}
            </select>
          </label>
          <label className="rl-toolbar-group">
            Sort
            <select
              value={sortKey ?? ""}
              onChange={(e) => setSortKey(e.target.value || null)}
            >
              <option value="">Default</option>
              {visible.map((c) => (
                <option key={c} value={c}>
                  {columnLabel(c, columnConfig[c])}
                </option>
              ))}
            </select>
          </label>
          <button
            className="rl-btn rl-sort-dir"
            onClick={() => setAsc((v) => !v)}
            disabled={!sortKey}
            aria-label="Toggle sort direction"
          >
            {asc ? "↑" : "↓"}
          </button>
          <span className="rl-toolbar-count">{sorted.length.toLocaleString()} rows</span>
          {drill.length > 0 && (
            <div className="rl-drill-chips">
              {drill.map((d, i) => (
                <button key={`${d.col}-${d.value}`} className="rl-chip" onClick={() => onRemoveDrill?.(i)}>
                  {d.value}
                  <span className="rl-chip-x">✕</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="rl-mcards">
          {groups
            ? groups.map(([key, gRows]) => {
                const isCollapsed = collapsed.has(key);
                return (
                  <div className="rl-mgroup" key={key}>
                    <button className="rl-mgroup-head" onClick={() => toggleGroup(key)}>
                      <span className="rl-caret">{isCollapsed ? "▸" : "▾"}</span>
                      <span className="rl-mgroup-title">{String(gRows[0]?.[groupBy] ?? key)}</span>
                      <span className="rl-group-count">{gRows.length}</span>
                    </button>
                    {!isCollapsed && gRows.map((row, ri) => renderCard(row, ri))}
                  </div>
                );
              })
            : sorted.slice(0, cardLimit).map((row, ri) => renderCard(row, ri))}
        </div>
        {!groups && sorted.length > cardLimit && (
          <div ref={sentinelRef} className="rl-loadmore-sentinel">
            <span className="rl-spinner" /> Loading more…{" "}
            {(sorted.length - cardLimit).toLocaleString()} left
          </div>
        )}

        <RowDrawer
          row={detailRow}
          columns={visible}
          columnConfig={columnConfig}
          title={firstCol ? String(detailRow?.[firstCol] ?? "Row detail") : "Row detail"}
          onClose={() => setDetailRow(null)}
        />
      </div>
    );
  }

  return (
    <div>
      <div className="rl-toolbar rl-no-print">
        <input
          className="rl-toolbar-search"
          type="search"
          placeholder="Filter rows…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        <span className="rl-toolbar-count">
          {sorted.length.toLocaleString()}
          {sorted.length !== rows.length ? ` / ${rows.length.toLocaleString()}` : ""} rows
        </span>
        {drill.length > 0 && (
          <div className="rl-drill-chips">
            {drill.map((d, i) => (
              <button
                key={`${d.col}-${d.value}`}
                className="rl-chip"
                onClick={() => onRemoveDrill?.(i)}
                title="Remove filter"
              >
                <span className="rl-chip-key">{columnLabel(d.col, columnConfig[d.col])}</span>
                {d.value}
                <span className="rl-chip-x">✕</span>
              </button>
            ))}
            {drill.length > 1 && (
              <button className="rl-chip rl-chip-clear" onClick={() => onClearDrill?.()}>
                Clear all
              </button>
            )}
          </div>
        )}
        <div className="rl-toolbar-right">
          <label className="rl-toolbar-group">
            Group by
            <select value={groupBy} onChange={(e) => setGroupBy(e.target.value)}>
              <option value="">None</option>
              {visible.map((c) => (
                <option key={c} value={c}>
                  {columnLabel(c, columnConfig[c])}
                </option>
              ))}
            </select>
          </label>
          <div className="rl-seg">
            <button className={!compact ? "is-active" : ""} onClick={() => setCompact(false)}>
              Comfortable
            </button>
            <button className={compact ? "is-active" : ""} onClick={() => setCompact(true)}>
              Compact
            </button>
          </div>
          <div className="rl-cols-menu">
            <button className="rl-btn" onClick={() => setShowColsPanel((v) => !v)}>
              Columns
            </button>
            {showColsPanel && (
              <div className="rl-cols-panel">
                {allCols.map((c) => (
                  <label key={c}>
                    <input
                      type="checkbox"
                      checked={!hiddenCols.has(c)}
                      onChange={() => toggleCol(c)}
                    />
                    {columnLabel(c, columnConfig[c])}
                  </label>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className={`rl-table-wrap${compact ? " rl-compact" : ""}`}>
        <table className="rl-table">
          <thead>
            {hasBands && (
              <tr className="rl-band-row">
                {bands.map((b, i) => (
                  <th key={i} colSpan={b.span} className="rl-band">
                    {b.label}
                  </th>
                ))}
              </tr>
            )}
            <tr ref={headRef} className="rl-head-row">
              {visible.map((c, i) => (
                <th
                  key={c}
                  className={[numericByCol[c] ? "rl-num" : "", stickyClass(i)]
                    .filter(Boolean)
                    .join(" ") || undefined}
                  style={i < FROZEN ? stickyStyle(i) : undefined}
                  onClick={() => onSort(c)}
                  title="Sort"
                >
                  {columnLabel(c, columnConfig[c])}
                  {sortKey === c && <span className="rl-sort-ind">{asc ? "▲" : "▼"}</span>}
                </th>
              ))}
            </tr>
          </thead>

          {groups ? (
            groups.map(([key, gRows]) => {
              const isCollapsed = collapsed.has(key);
              return (
                <tbody key={key} className="rl-group">
                  <tr className="rl-group-row" onClick={() => toggleGroup(key)}>
                    {visible.map((c, i) => {
                      const cls = [numericByCol[c] ? "rl-num" : "", stickyClass(i)]
                        .filter(Boolean)
                        .join(" ");
                      const sticky = i < FROZEN ? stickyStyle(i) : {};
                      if (i === 0) {
                        return (
                          <td key={c} className={cls || undefined} style={sticky}>
                            <span className="rl-caret">{isCollapsed ? "▸" : "▾"}</span>
                            {String(gRows[0]?.[groupBy] ?? key)}
                            <span className="rl-group-count">{gRows.length}</span>
                          </td>
                        );
                      }
                      return (
                        <td key={c} className={cls || undefined} style={sticky}>
                          {subtotal(gRows, c)}
                        </td>
                      );
                    })}
                  </tr>
                  {!isCollapsed &&
                    gRows.map((row, ri) => (
                      <tr key={ri} className="rl-data-row" onClick={() => setDetailRow(row)}>
                        {visible.map((c, i) => cell(c, i, row))}
                      </tr>
                    ))}
                </tbody>
              );
            })
          ) : (
            <tbody>
              {sorted.map((row, ri) => (
                <tr key={ri} className="rl-data-row" onClick={() => setDetailRow(row)}>
                  {visible.map((c, i) => cell(c, i, row))}
                </tr>
              ))}
            </tbody>
          )}
        </table>
      </div>
      {colCount === 0 && <p className="rl-empty">All columns hidden.</p>}
      <RowDrawer
        row={detailRow}
        columns={visible}
        columnConfig={columnConfig}
        title={firstCol ? String(detailRow?.[firstCol] ?? "Row detail") : "Row detail"}
        onClose={() => setDetailRow(null)}
      />
    </div>
  );
}
