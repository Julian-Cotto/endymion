import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useMediaQuery } from "../hooks/useMediaQuery";
import {
  createDefinition,
  getDefinition,
  previewDefinition,
  updateDefinition,
} from "../services/reportsApi";
import type {
  ChartConfig,
  ColumnConfig,
  CombineSpec,
  LayoutBlock,
  OutputType,
  ParamSpec,
  PreviewResult,
  ReportDefinitionInput,
  SourceInput,
} from "../types/reports";
import type { ReportView } from "../types/reports";
import { navigate } from "../hooks/useHashRoute";
import { useToast } from "../components/Toast";
import { LayoutEditor } from "../components/reports/LayoutEditor";
import { ReportRenderer } from "../components/reports/ReportRenderer";
import { SourceEditor } from "../components/reports/SourceEditor";
import { ExpandableTextarea } from "../components/reports/ExpandableTextarea";
import { MetadataEditor } from "../components/reports/MetadataEditor";
import type { MetaShape } from "../components/reports/MetadataEditor";

const TEMPLATE = `{
  "columns": {
    "region": { "label": "Region" },
    "n": { "label": "Count", "format": "int" }
  },
  "chart": { "type": "bar", "x": "region", "y": "n" },
  "params": {}
}`;

const OUTPUTS: OutputType[] = ["table", "chart", "kpi"];

/** Sample rows (keyed by the metadata column names) so chart blocks preview
 * live in the editor before a real snapshot exists. */
function mockPreviewRows(
  columns: Record<string, { format?: string }>,
): Array<Record<string, unknown>> {
  const keys = Object.keys(columns);
  if (!keys.length) return [];
  const N = 8;
  return Array.from({ length: N }, (_, i) => {
    const row: Record<string, unknown> = {};
    for (const k of keys) {
      const fmt = columns[k]?.format;
      if (fmt === "int") row[k] = (i + 1) * 100 + (k.length % 7);
      else if (fmt === "float" || fmt === "currency")
        row[k] = Math.round(((i + 1) * 1234.5 + k.length) * 100) / 100;
      else if (fmt === "percent") row[k] = (i + 1) / N;
      else if (fmt === "date" || fmt === "datetime") row[k] = `2026-0${(i % 9) + 1}-15`;
      else row[k] = `${k} ${i + 1}`;
    }
    return row;
  });
}

/** Shared report form. Create mode when `slug` is undefined; edit mode
 * (prefill + PUT) when a slug is supplied. */
export function UploadView({ slug }: { slug?: string } = {}) {
  const isEdit = !!slug;
  const toast = useToast();

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [sql, setSql] = useState("");
  const [groups, setGroups] = useState("");
  const [meta, setMeta] = useState(TEMPLATE);
  const [outputs, setOutputs] = useState<OutputType[]>(["table"]);
  const [layout, setLayout] = useState<LayoutBlock[]>([]);
  const [status, setStatus] = useState<ReportDefinitionInput["status"]>("active");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(isEdit);

  // Data sources: legacy single SQL, or one-or-more blended sources/files.
  const [sourceMode, setSourceMode] = useState<"single" | "sources">("single");
  const [sources, setSources] = useState<SourceInput[]>([]);
  const [combine, setCombine] = useState<CombineSpec | null>(null);
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewing, setPreviewing] = useState(false);
  // Guards against stale preview responses (auto + manual) overwriting newer ones.
  const previewTokenRef = useRef(0);

  // Split-editor sizing: give each pane its own scroll within a viewport-tall
  // container on wide screens (two scrollbars); stack + single scroll on mobile.
  const layoutRef = useRef<HTMLDivElement>(null);
  const isWide = useMediaQuery("(min-width: 901px)");
  const [paneH, setPaneH] = useState<number | undefined>(undefined);

  // Draggable divider: form pane width (px), persisted across sessions.
  const [formWidth, setFormWidth] = useState<number>(() => {
    const saved = Number(localStorage.getItem("rl:editor:formWidth"));
    return saved >= 360 ? saved : 640;
  });
  const formWidthRef = useRef(formWidth);
  function onDividerDown(e: React.MouseEvent) {
    e.preventDefault();
    document.body.style.userSelect = "none";
    document.body.style.cursor = "col-resize";
    const onMove = (ev: MouseEvent) => {
      const el = layoutRef.current;
      if (!el) return;
      const left = el.getBoundingClientRect().left;
      const w = Math.min(el.clientWidth - 380, Math.max(360, ev.clientX - left));
      formWidthRef.current = w;
      setFormWidth(w);
    };
    const onUp = () => {
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
      try {
        localStorage.setItem("rl:editor:formWidth", String(Math.round(formWidthRef.current)));
      } catch {
        /* ignore */
      }
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }
  useLayoutEffect(() => {
    if (!isWide) {
      setPaneH(undefined);
      return;
    }
    const measure = () => {
      const el = layoutRef.current;
      if (!el) return;
      setPaneH(Math.max(360, window.innerHeight - el.getBoundingClientRect().top - 12));
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [isWide, loading]);

  useEffect(() => {
    if (!slug) return;
    setLoading(true);
    getDefinition(slug)
      .then((d) => {
        setTitle(d.title);
        setDescription(d.description ?? "");
        setSql(d.sql_text ?? "");
        if (d.sources && d.sources.length) {
          setSourceMode("sources");
          setSources(
            d.sources.map((s) => ({
              name: s.name,
              type: s.source_type,
              sql: s.sql_text ?? "",
              file_ref: s.file_ref ?? undefined,
              params: s.params,
              sort_order: s.sort_order,
            })),
          );
          setCombine(d.combine ?? null);
        } else {
          setSourceMode("single");
        }
        setGroups((d.access_groups ?? []).join(", "));
        setOutputs((d.output_types?.length ? d.output_types : ["table"]) as OutputType[]);
        setStatus(d.status as ReportDefinitionInput["status"]);
        setLayout((d.layout as LayoutBlock[]) ?? []);
        setMeta(
          JSON.stringify(
            { columns: d.columns ?? {}, chart: d.chart ?? null, params: d.params ?? {} },
            null,
            2,
          ),
        );
        setError(null);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [slug]);

  // ---- Unsaved-changes guard --------------------------------------------
  const formSig = JSON.stringify({
    title,
    description,
    sql,
    groups,
    meta,
    outputs,
    layout,
    status,
    sourceMode,
    sources,
    combine,
  });
  const baselineRef = useRef<string | null>(null);
  useEffect(() => {
    // Capture the baseline once the form has finished loading (create or edit).
    if (!loading && baselineRef.current === null) baselineRef.current = formSig;
  }, [loading, formSig]);
  const dirty = baselineRef.current !== null && formSig !== baselineRef.current;

  useEffect(() => {
    if (!dirty) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  // ---- Debounced auto-preview: refresh real-data preview after edits ----
  useEffect(() => {
    if (loading) return;
    const hasData =
      sourceMode === "sources"
        ? sources.some((s) => (s.type === "sql" ? !!s.sql?.trim() : !!s.file_ref))
        : !!sql.trim();
    if (!hasData) return;
    const handle = window.setTimeout(() => {
      let input: ReportDefinitionInput;
      try {
        input = buildInput();
      } catch {
        return; // invalid metadata JSON mid-edit — skip this round
      }
      const token = ++previewTokenRef.current;
      previewDefinition(input)
        .then((p) => {
          if (token === previewTokenRef.current) {
            setPreview(p);
            setPreviewError(null);
          }
        })
        .catch(() => {
          /* silent for auto-preview; the manual button surfaces errors */
        });
    }, 800);
    return () => window.clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, sourceMode, sql, JSON.stringify(sources), JSON.stringify(combine), meta]);

  /** Navigate away, confirming first if there are unsaved edits. */
  function leave(go: () => void) {
    if (dirty && !window.confirm("You have unsaved changes. Discard them?")) return;
    go();
  }

  function toggleOutput(o: OutputType) {
    setOutputs((cur) =>
      cur.includes(o) ? cur.filter((x) => x !== o) : [...cur, o],
    );
  }

  /** Assemble the API payload from form state. Throws if metadata JSON is bad. */
  function buildInput(): ReportDefinitionInput {
    let parsedMeta: Record<string, unknown> = {};
    if (meta.trim()) parsedMeta = JSON.parse(meta);

    const input: ReportDefinitionInput = {
      title: title.trim(),
      description: description.trim(),
      status,
      output_types: outputs.length ? outputs : ["table"],
      access_groups: groups
        .split(",")
        .map((g) => g.trim())
        .filter(Boolean),
      columns: (parsedMeta.columns as never) ?? {},
      params: (parsedMeta.params as never) ?? {},
      chart: (parsedMeta.chart as never) ?? null,
      layout: layout.length ? layout : null,
    };
    if (sourceMode === "sources") {
      input.sources = sources;
      input.combine = sources.length >= 2 ? combine : null;
    } else {
      input.sql_text = sql;
    }
    return input;
  }

  async function onPreview() {
    setPreviewError(null);
    let input: ReportDefinitionInput;
    try {
      input = buildInput();
    } catch (err) {
      setPreviewError(
        `Metadata is not valid JSON: ${
          err instanceof Error ? err.message : "parse error"
        }`,
      );
      return;
    }
    setPreviewing(true);
    const token = ++previewTokenRef.current;
    try {
      const p = await previewDefinition(input);
      if (token === previewTokenRef.current) setPreview(p);
    } catch (err) {
      if (token === previewTokenRef.current) {
        setPreview(null);
        setPreviewError(err instanceof Error ? err.message : "Preview failed.");
      }
    } finally {
      if (token === previewTokenRef.current) setPreviewing(false);
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    let input: ReportDefinitionInput;
    try {
      input = buildInput();
    } catch (err) {
      setError(
        `Metadata is not valid JSON: ${
          err instanceof Error ? err.message : "parse error"
        }`,
      );
      return;
    }

    setSubmitting(true);
    try {
      const saved = isEdit
        ? await updateDefinition(slug as string, input)
        : await createDefinition(input);
      toast("success", isEdit ? "Report updated" : "Report published");
      navigate({ view: "report", slug: saved.slug });
    } catch (err) {
      // Backend 422 messages (SQL guard / undeclared params) surface here.
      setError(
        err instanceof Error
          ? err.message
          : `Failed to ${isEdit ? "save" : "create"} report.`,
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return <p className="rl-loading">Loading report…</p>;
  }

  const split = isWide && paneH !== undefined;

  // Columns + sample rows for chart-block field pickers and live preview.
  let parsedMetaLive: Record<string, unknown> = {};
  try {
    parsedMetaLive = JSON.parse(meta || "{}") ?? {};
  } catch {
    /* invalid JSON while typing — leave empty */
  }
  const columnsMeta =
    parsedMetaLive.columns && typeof parsedMetaLive.columns === "object"
      ? (parsedMetaLive.columns as Record<string, { format?: string }>)
      : {};
  const paramsMeta =
    parsedMetaLive.params && typeof parsedMetaLive.params === "object"
      ? (parsedMetaLive.params as Record<string, ParamSpec>)
      : {};
  const chartMeta = (parsedMetaLive.chart as ChartConfig | null) ?? null;
  const availableColumns = Object.keys(columnsMeta);
  const previewRows = mockPreviewRows(columnsMeta);

  // Columns offered to the chart pickers: those defined, plus any detected by a
  // dry-run preview.
  const metaColumnKeys = Array.from(
    new Set([...availableColumns, ...(preview?.result_columns ?? [])]),
  );

  // Structured editors write back into the single `meta` JSON string, which
  // stays the source of truth (buildInput parses it; the Advanced box mirrors it).
  function updateMeta(next: MetaShape) {
    setMeta(
      JSON.stringify(
        { columns: next.columns, chart: next.chart, params: next.params },
        null,
        2,
      ),
    );
  }

  // A synthetic ReportView so the right pane renders the whole composed page
  // (KPIs + charts + table) live from sample rows as you build.
  // Prefer real dry-run rows once the author has previewed; else sample rows.
  const usingRealPreview = preview !== null;
  const renderRows = usingRealPreview ? preview.rows : previewRows;
  const renderCols = usingRealPreview ? preview.result_columns : availableColumns;
  const previewView: ReportView = {
    slug: "__preview__",
    title: title || "Untitled report",
    description,
    output_types: outputs,
    layout: layout.length ? layout : null,
    columns: columnsMeta as never,
    chart: (parsedMetaLive.chart as never) ?? null,
    result_columns: renderCols,
    rows: renderRows,
    row_count: renderRows.length,
    snapshot_at: null,
    snapshot_status: null,
    stale: false,
  };

  return (
    <div
      ref={layoutRef}
      className={`rl-editor-layout${split ? " rl-editor-split" : ""}`}
      style={
        split
          ? { height: paneH, gridTemplateColumns: `${formWidth}px 10px minmax(0, 1fr)` }
          : undefined
      }
    >
      <form onSubmit={onSubmit} className="rl-editor-form">
      {isEdit && (
        <button
          type="button"
          className="rl-back"
          onClick={() => leave(() => navigate({ view: "report", slug: slug as string }))}
        >
          ← Back to report
        </button>
      )}

      <p className="rl-hint" style={{ marginBottom: 20 }}>
        {isEdit ? (
          <>
            Edit the report logic. Saving re-runs the query and refreshes the
            cached snapshot immediately.
          </>
        ) : (
          <>
            Upload the report logic — a read-only <strong>SELECT</strong> query
            and display metadata. The platform runs it against Snowflake and
            renders it with the shared, consistent report layout.
          </>
        )}
      </p>

      <p className="rl-hint" style={{ marginTop: -12, marginBottom: 16 }}>
        New here?{" "}
        <a href="#/help" onClick={() => navigate({ view: "help" })}>
          Read the builder guide →
        </a>
      </p>

      {error && <div className="rl-banner rl-banner-error">{error}</div>}

      <div className="rl-field">
        <label htmlFor="rl-title">Title</label>
        <input
          id="rl-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Active Policies by Region"
          required
        />
        <span className="rl-hint">
          {isEdit
            ? "The slug stays the same when you edit — links keep working."
            : "The slug is derived from this (e.g. active-policies-by-region)."}
        </span>
      </div>

      <div className="rl-field">
        <label htmlFor="rl-desc">Description</label>
        <ExpandableTextarea
          id="rl-desc"
          label="Description"
          value={description}
          onChange={setDescription}
          placeholder="What this report shows and who it's for."
          rows={2}
        />
      </div>

      <div className="rl-field">
        <label>Data source</label>
        <div className="rl-actions">
          <button
            type="button"
            className={sourceMode === "single" ? "rl-btn rl-btn-primary" : "rl-btn"}
            onClick={() => setSourceMode("single")}
          >
            Single SQL query
          </button>
          <button
            type="button"
            className={sourceMode === "sources" ? "rl-btn rl-btn-primary" : "rl-btn"}
            onClick={() => {
              setSourceMode("sources");
              if (!sources.length)
                setSources([{ name: "source_a", type: "sql", sql: "" }]);
            }}
          >
            Multiple sources / files
          </button>
        </div>
        <span className="rl-hint">
          Blend multiple SQL queries and/or uploaded CSV/XLSX files, or keep a
          single query.
        </span>
      </div>

      {sourceMode === "single" ? (
        <div className="rl-field">
          <label htmlFor="rl-sql">SQL (read-only SELECT)</label>
          <ExpandableTextarea
            id="rl-sql"
            label="SQL (read-only SELECT)"
            value={sql}
            onChange={setSql}
            placeholder={"SELECT region, COUNT(*) AS n\nFROM policies\nGROUP BY region"}
            rows={4}
            monospace
          />
          <span className="rl-hint">
            Use <code>:name</code> bind params; declare them in metadata below.
          </span>
        </div>
      ) : (
        <div className="rl-field">
          <label>Sources</label>
          <SourceEditor
            sources={sources}
            combine={combine}
            onSourcesChange={setSources}
            onCombineChange={setCombine}
          />
        </div>
      )}

      <div className="rl-field">
        <div className="rl-actions">
          <button
            type="button"
            className="rl-btn"
            onClick={onPreview}
            disabled={previewing}
          >
            {previewing ? "Previewing…" : "Preview data"}
          </button>
          {preview && (
            <span className="rl-hint">
              {preview.row_count} rows · {preview.result_columns.join(", ")}
            </span>
          )}
        </div>
        <span className="rl-hint">Preview auto-refreshes as you edit; click to refresh now.</span>
        {previewError && (
          <div className="rl-banner rl-banner-error">{previewError}</div>
        )}
      </div>

      <div className="rl-field">
        <label>Outputs</label>
        <div className="rl-actions">
          {OUTPUTS.map((o) => (
            <button
              type="button"
              key={o}
              className={outputs.includes(o) ? "rl-btn rl-btn-primary" : "rl-btn"}
              onClick={() => toggleOutput(o)}
            >
              {o}
            </button>
          ))}
        </div>
      </div>

      <div className="rl-field">
        <label htmlFor="rl-groups">Access groups (comma-separated)</label>
        <input
          id="rl-groups"
          value={groups}
          onChange={(e) => setGroups(e.target.value)}
          placeholder="underwriting, exec"
        />
        <span className="rl-hint">
          Leave blank to make the report visible to all viewers.
        </span>
      </div>

      <div className="rl-field">
        <label>Display metadata</label>
        <MetadataEditor
          columns={columnsMeta as Record<string, ColumnConfig>}
          params={paramsMeta}
          chart={chartMeta}
          columnKeys={metaColumnKeys}
          sampleRows={preview?.rows ?? []}
          onChange={updateMeta}
        />
        <details className="rl-advanced">
          <summary className="rl-hint">Advanced: raw JSON</summary>
          <ExpandableTextarea
            id="rl-meta"
            label="Display metadata (JSON)"
            value={meta}
            onChange={setMeta}
            rows={8}
            monospace
            spellCheck={false}
            json
          />
          <span className="rl-hint">
            columns (labels + formats), chart hints, and param specs. Extra
            column hints (bar/heat/badge/group) live here.
          </span>
        </details>
      </div>

      <div className="rl-field">
        <label>Page layout</label>
        <span className="rl-hint" style={{ marginBottom: 8 }}>
          Compose the report into blocks (KPIs, charts, tables, notes) in a
          12-column grid. Leave empty to use the default stacked layout.
        </span>
        <LayoutEditor
          value={layout}
          onChange={setLayout}
          columns={availableColumns}
          previewRows={previewRows}
        />
      </div>

      <div className="rl-actions">
        <button className="rl-btn rl-btn-primary" type="submit" disabled={submitting}>
          {submitting
            ? isEdit
              ? "Saving…"
              : "Publishing…"
            : isEdit
              ? "Save changes"
              : "Publish report"}
        </button>
        <button
          type="button"
          className="rl-btn"
          onClick={() =>
            leave(() =>
              navigate(
                isEdit
                  ? { view: "report", slug: slug as string }
                  : { view: "browse" },
              ),
            )
          }
        >
          Cancel
        </button>
      </div>
      </form>

      {split && (
        <div
          className="rl-divider"
          onMouseDown={onDividerDown}
          role="separator"
          aria-orientation="vertical"
          title="Drag to resize"
        />
      )}

      <aside className="rl-editor-preview">
        <div className="rl-preview-head">
          Live preview{" "}
          <span className="rl-preview-badge">
            {usingRealPreview ? "real data" : "sample data"}
          </span>
        </div>
        {renderRows.length || availableColumns.length ? (
          <div className="rl-preview-body">
            <ReportRenderer report={previewView} />
          </div>
        ) : (
          <p className="rl-hint">
            Define columns in the metadata, or click “Preview data”, to see the
            composed page.
          </p>
        )}
      </aside>
    </div>
  );
}
