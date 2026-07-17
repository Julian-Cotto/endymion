import { useEffect } from "react";
import type { ColumnConfig } from "../../types/reports";
import { columnLabel, formatValue } from "./format";

type Row = Record<string, unknown>;

/** Slide-out panel showing one row as a clean label/value list. */
export function RowDrawer({
  row,
  columns,
  columnConfig,
  title,
  onClose,
}: {
  row: Row | null;
  columns: string[];
  columnConfig: Record<string, ColumnConfig>;
  title?: string;
  onClose: () => void;
}) {
  useEffect(() => {
    if (!row) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [row, onClose]);

  if (!row) return null;

  return (
    <div className="rl-drawer-overlay rl-no-print" onClick={onClose}>
      <aside
        className="rl-drawer"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Row details"
      >
        <header className="rl-drawer-head">
          <h4>{title ?? "Row detail"}</h4>
          <button className="rl-drawer-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </header>
        <dl className="rl-drawer-list">
          {columns
            .filter((c) => !columnConfig[c]?.hidden)
            .map((c) => (
              <div className="rl-drawer-row" key={c}>
                <dt>{columnLabel(c, columnConfig[c])}</dt>
                <dd>{formatValue(row[c], columnConfig[c])}</dd>
              </div>
            ))}
        </dl>
      </aside>
    </div>
  );
}
