import { apiGet, apiPost, apiPut, buildUrl } from "./apiClient";
import { resolveFeatureAuthContext } from "../platform/authAdapter";
import type {
  ReportDefinition,
  ReportDefinitionInput,
  ReportSummary,
  ReportView,
} from "../types/reports";

const BASE = "/reports-layering";

export function listReports(): Promise<ReportSummary[]> {
  return apiGet<ReportSummary[]>(`${BASE}/reports`);
}

export function getReport(slug: string): Promise<ReportView> {
  return apiGet<ReportView>(`${BASE}/reports/${encodeURIComponent(slug)}`);
}

export function listDefinitions(): Promise<ReportDefinition[]> {
  return apiGet<ReportDefinition[]>(`${BASE}/definitions`);
}

/** Full definition incl. SQL — author only. Used to prefill the edit form. */
export function getDefinition(slug: string): Promise<ReportDefinition> {
  return apiGet<ReportDefinition>(
    `${BASE}/definitions/${encodeURIComponent(slug)}`,
  );
}

export function createDefinition(
  input: ReportDefinitionInput,
): Promise<ReportDefinition> {
  return apiPost<ReportDefinition>(`${BASE}/definitions`, input);
}

export function updateDefinition(
  slug: string,
  input: ReportDefinitionInput,
): Promise<ReportDefinition> {
  return apiPut<ReportDefinition>(
    `${BASE}/definitions/${encodeURIComponent(slug)}`,
    input,
  );
}

export function refreshDefinition(slug: string): Promise<ReportDefinition> {
  return apiPost<ReportDefinition>(
    `${BASE}/definitions/${encodeURIComponent(slug)}/refresh`,
  );
}

/** CSV export is a file download, so it bypasses the JSON client. */
export async function downloadReportCsv(slug: string): Promise<void> {
  const url = buildUrl(`${BASE}/reports/${encodeURIComponent(slug)}/export.csv`);
  const auth = resolveFeatureAuthContext();
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${auth.accessToken}` },
  });
  if (!res.ok) {
    throw new Error(`Export failed: ${res.status} ${res.statusText}`);
  }
  const blob = await res.blob();
  const href = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = href;
  a.download = `${slug}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(href);
}
