import { useCallback, useEffect, useState } from "react";
import {
  downloadReportCsv,
  getReport,
  refreshDefinition,
} from "../services/reportsApi";
import type { ReportView as ReportViewData } from "../types/reports";
import { ReportRenderer } from "../components/reports/ReportRenderer";
import { navigate } from "../hooks/useHashRoute";
import { exactTime, relativeTime } from "../utils/time";
import { ReportSkeleton } from "../components/reports/Skeletons";
import { useToast } from "../components/Toast";

export function ReportView({
  slug,
  canEdit = false,
}: {
  slug: string;
  canEdit?: boolean;
}) {
  const [report, setReport] = useState<ReportViewData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [offline, setOffline] = useState(false);
  const toast = useToast();

  const load = useCallback(() => {
    setReport(null);
    setError(null);
    setOffline(false);
    const cacheKey = `rl:cache:${slug}`;
    getReport(slug)
      .then((r) => {
        setReport(r);
        try {
          localStorage.setItem(cacheKey, JSON.stringify(r));
        } catch {
          /* quota — skip caching */
        }
      })
      .catch((e: Error) => {
        // Offline / server unreachable: fall back to the last cached snapshot.
        try {
          const cached = localStorage.getItem(cacheKey);
          if (cached) {
            setReport(JSON.parse(cached) as ReportViewData);
            setOffline(true);
            return;
          }
        } catch {
          /* ignore */
        }
        setError(e.message);
      });
  }, [slug]);

  useEffect(() => {
    load();
  }, [load]);

  async function onRefresh() {
    setRefreshing(true);
    setError(null);
    try {
      await refreshDefinition(slug);
      load();
      toast("success", "Snapshot refreshed");
    } catch (e) {
      // 502 here means the snapshot ran but the Snowflake query failed.
      const msg = e instanceof Error ? e.message : "Refresh failed";
      setError(msg);
      toast("error", "Refresh failed");
    } finally {
      setRefreshing(false);
    }
  }

  async function onExportCsv() {
    setExporting(true);
    try {
      await downloadReportCsv(slug);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div>
      <button className="rl-back" onClick={() => navigate({ view: "browse" })}>
        ← All reports
      </button>

      {error && <div className="rl-banner rl-banner-error">{error}</div>}
      {offline && (
        <div className="rl-banner rl-banner-warn">
          You're offline — showing the last cached snapshot for this report.
        </div>
      )}
      {!report && !error && <ReportSkeleton />}

      {report && (
        <>
          <div className="rl-report-head">
            <h2>{report.title}</h2>
            {report.description && <p>{report.description}</p>}
            <div className="rl-meta">
              <span className="rl-status-dot" data-state={report.snapshot_status === "error" ? "error" : report.snapshot_at ? "ok" : "none"} />
              {report.snapshot_at ? (
                <span title={exactTime(report.snapshot_at)}>
                  Updated {relativeTime(report.snapshot_at)}
                </span>
              ) : (
                <span className="rl-stale">No snapshot yet</span>
              )}
              {report.snapshot_status === "error" && (
                <span className="rl-stale">Last refresh failed</span>
              )}
              <span>·</span>
              <span>{report.row_count.toLocaleString()} rows</span>
              <div className="rl-actions rl-no-print" style={{ marginLeft: "auto" }}>
                {canEdit && (
                  <button
                    className="rl-btn"
                    onClick={onRefresh}
                    disabled={refreshing}
                  >
                    {refreshing ? "Refreshing…" : "Refresh data"}
                  </button>
                )}
                {canEdit && (
                  <button
                    className="rl-btn"
                    onClick={() => navigate({ view: "edit", slug })}
                  >
                    Edit
                  </button>
                )}
                <button
                  className="rl-btn"
                  onClick={onExportCsv}
                  disabled={exporting || report.row_count === 0}
                >
                  {exporting ? "Exporting…" : "Export CSV"}
                </button>
                <button
                  className="rl-btn"
                  onClick={() => window.print()}
                  disabled={report.row_count === 0}
                >
                  Export PDF
                </button>
              </div>
            </div>
          </div>

          <ReportRenderer report={report} />
        </>
      )}
    </div>
  );
}
