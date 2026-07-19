import { apiGet, apiPost, apiPut, buildUrl } from "./apiClient";
import { resolveFeatureAuthContext } from "../platform/authAdapter";
import type {
  PreviewResult,
  ReportDefinition,
  ReportDefinitionInput,
  ReportSummary,
  ReportView,
  UploadedDataset,
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

/** Dry-run: real columns + sample rows for an unsaved definition. */
export function previewDefinition(
  input: ReportDefinitionInput,
): Promise<PreviewResult> {
  return apiPost<PreviewResult>(`${BASE}/definitions/preview`, input);
}

/** Upload a CSV/XLSX and get back a file_ref + inferred columns. Multipart, so
 * it bypasses the JSON client (which would force a Content-Type). */
export async function uploadDataset(file: File): Promise<UploadedDataset> {
  const url = buildUrl(`${BASE}/uploads`);
  const auth = resolveFeatureAuthContext();
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(url, {
    method: "POST",
    headers: { Authorization: `Bearer ${auth.accessToken}` },
    body: form,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(
      `Upload failed: ${res.status} ${res.statusText}${body ? ` - ${body}` : ""}`,
    );
  }
  return (await res.json()) as UploadedDataset;
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
