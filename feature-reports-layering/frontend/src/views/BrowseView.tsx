import { useEffect, useMemo, useState } from "react";
import { listReports } from "../services/reportsApi";
import type { ReportSummary } from "../types/reports";
import { navigate } from "../hooks/useHashRoute";
import { relativeTime } from "../utils/time";
import { CardGridSkeleton } from "../components/reports/Skeletons";
import { EmptyState } from "../components/reports/EmptyState";

export function BrowseView({ canAuthor = false }: { canAuthor?: boolean }) {
  const [reports, setReports] = useState<ReportSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    listReports()
      .then(setReports)
      .catch((e: Error) => setError(e.message));
  }, []);

  const filtered = useMemo(() => {
    if (!reports) return [];
    const q = query.trim().toLowerCase();
    if (!q) return reports;
    return reports.filter(
      (r) =>
        r.title.toLowerCase().includes(q) ||
        r.description.toLowerCase().includes(q),
    );
  }, [reports, query]);

  if (error) return <p className="rl-error">Failed to load reports: {error}</p>;
  if (!reports) return <CardGridSkeleton />;

  return (
    <div>
      <div className="rl-field" style={{ maxWidth: 360 }}>
        <input
          type="search"
          placeholder="Search reports…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search reports"
        />
      </div>

      {filtered.length === 0 ? (
        reports.length === 0 ? (
          <EmptyState
            title="No reports yet"
            hint={
              canAuthor
                ? "Upload a SQL query and the platform renders it as a polished report."
                : "You don't have access to any reports yet. Ask an author to grant your group."
            }
            action={
              canAuthor ? (
                <button
                  className="rl-btn rl-btn-primary"
                  onClick={() => navigate({ view: "upload" })}
                >
                  Create your first report
                </button>
              ) : undefined
            }
          />
        ) : (
          <p className="rl-empty">No reports match your search.</p>
        )
      ) : (
        <div className="rl-grid">
          {filtered.map((r) => (
            <button
              key={r.slug}
              className="rl-card rl-report-card"
              onClick={() => navigate({ view: "report", slug: r.slug })}
              style={{ textAlign: "left" }}
            >
              <h3>{r.title}</h3>
              {r.description && <p>{r.description}</p>}
              <div className="rl-card-meta">
                <span
                  className="rl-status-dot"
                  data-state={
                    r.last_snapshot_status === "error"
                      ? "error"
                      : r.last_snapshot_at
                        ? "ok"
                        : "none"
                  }
                />
                {r.last_snapshot_at
                  ? `Updated ${relativeTime(r.last_snapshot_at)}`
                  : "No data yet"}
              </div>
              <div className="rl-tagrow">
                {r.is_live === false && (
                  <span className="rl-tag" style={{ color: "var(--rl-warn)" }}>
                    private
                  </span>
                )}
                {r.output_types.map((t) => (
                  <span className="rl-tag" key={t}>
                    {t}
                  </span>
                ))}
                {r.last_snapshot_status === "error" && (
                  <span className="rl-tag" style={{ color: "var(--rl-danger)" }}>
                    snapshot error
                  </span>
                )}
                {!r.last_snapshot_at && (
                  <span className="rl-tag" style={{ color: "var(--rl-warn)" }}>
                    no data yet
                  </span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
