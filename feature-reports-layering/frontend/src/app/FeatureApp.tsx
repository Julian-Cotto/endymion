import "../styles/reports.css";
import type { ShellMountContext } from "../platform/shellContext";
import { navigate, useHashRoute } from "../hooks/useHashRoute";
import { BrowseView } from "../views/BrowseView";
import { DashboardView } from "../views/DashboardView";
import { ReportView } from "../views/ReportView";
import { UploadView } from "../views/UploadView";
import { useFeatureAuth } from "../platform/authProvider";
import { ToastProvider } from "../components/Toast";

const CAN_AUTHOR = new Set([
  "reports-layering.create",
  "reports-layering.edit",
  "reports-layering.admin",
  "platform.admin",
]);

export function FeatureApp({
  shellContext: _shellContext,
}: {
  shellContext?: ShellMountContext;
}) {
  const route = useHashRoute();
  const auth = useFeatureAuth();
  const canAuthor = (auth.roles ?? []).some((r: string) => CAN_AUTHOR.has(r));

  if (!auth.isAuthenticated && auth.authMode === "entra") {
    return (
      <div className="rl-root">
        <div className="rl-shell">
          <h1>Reports Layering</h1>
          <p className="rl-empty">This feature requires shell authentication.</p>
        </div>
      </div>
    );
  }

  return (
    <ToastProvider>
      <div className="rl-root">
        <div className="rl-shell">
          <header className="rl-topbar">
            <nav className="rl-nav rl-no-print">
              <button
                className={route.view === "dashboard" ? "is-active" : ""}
                onClick={() => navigate({ view: "dashboard" })}
              >
                Dashboard
              </button>
              <button
                className={
                  route.view === "browse" || route.view === "report" ? "is-active" : ""
                }
                onClick={() => navigate({ view: "browse" })}
              >
                Browse
              </button>
              {canAuthor && (
                <button
                  className={route.view === "upload" ? "is-active" : ""}
                  onClick={() => navigate({ view: "upload" })}
                >
                  Upload
                </button>
              )}
            </nav>
          </header>

          <main>
            {route.view === "dashboard" && <DashboardView />}
            {route.view === "browse" && <BrowseView canAuthor={canAuthor} />}
            {route.view === "report" && (
              <ReportView slug={route.slug} canEdit={canAuthor} />
            )}
            {(route.view === "upload" || route.view === "edit") &&
              (canAuthor ? (
                <UploadView slug={route.view === "edit" ? route.slug : undefined} />
              ) : (
                <p className="rl-error">
                  You don't have permission to edit reports.
                </p>
              ))}
          </main>
        </div>
      </div>
    </ToastProvider>
  );
}
