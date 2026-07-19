# Reporting Layer — Enhancements Plan

Action items for three enhancements to the reports-layering feature:

1. **File sources** — accept CSV / XLSX as a view's data, not only SQL.
2. **Multi-source views** — marry (join / union) multiple data sources into one view.
3. **Builder upgrade** — more controls and better visibility in the upload/builder UI.

## Guiding decisions

- **Items 1 and 2 are one feature at different N.** A CSV report is "one non-SQL source";
  marrying sources is "N sources + a combine step." Build the **multi-source model first**;
  file upload falls out as the N=1 case. Building file-upload standalone first would mean
  tearing it apart later.
- **Blending runs in-process with pandas** (decided). The snapshot pipeline pulls each
  source's rows (SQL → Snowflake, file → stored dataset) and merges in Python, then caches
  one combined snapshot. No Snowflake staging / write access required. The renderer keeps
  consuming flat rows unchanged. Bounded by row/memory caps — acceptable for report-sized data.

## Current constraints (where the single-source assumption lives)

- `report_definitions.sql_text` is NOT NULL — a report *is* a query.
  `backend/app/models/report.py:35`
- `sql_guard.validate_read_only()` rejects anything but a single SELECT/WITH.
  `backend/app/services/reports/sql_guard.py:35`
- `refresh_snapshot()` runs exactly one `run_query(defn.sql_text, …)` and caches rows.
  `backend/app/services/reports/snapshots.py:91`
- Builder is a single SQL textarea + a raw JSON metadata textarea (columns/chart/params).
  `frontend/src/views/UploadView.tsx`

---

## Feature 2 — Multiple data sources per view (build first) — BACKEND DONE

- [x] New `report_sources` child table: `report_id`, `name`, `source_type` (`sql`|`file`),
      `sql_text` (nullable), `file_ref` (nullable), `params`, `sort_order`.
- [x] Add `combine` JSON spec to `report_definitions`:
      `{op: "join"|"union", joins: [{left, right, on: [[l,r]...], how: "inner"|"left"}], distinct}`.
- [x] Make `report_definitions.sql_text` **nullable**.
- [x] New Alembic migration `a1b2c3d4e5f6` (up + down verified on scratch SQLite).
- [x] Snapshot pipeline: resolve each source → DataFrame, apply `combine`, emit rows
      (`services/reports/blend.py` + `snapshots.py`). Legacy single-`sql_text` path preserved.
- [x] SQL guard runs per SQL source.
- [x] Tests: `tests/test_blend.py` (unit) + multi-source flow in `tests/test_reports_flow.py`.
- [ ] Column-collision policy is currently pandas suffix (`_<right>`); revisit for nicer UX.
- [ ] Guard rails still TODO: max combined rows cap, explicit join-key type coercion.
- [ ] Param namespace: per-source params modeled; UI surfacing (`source.param`) still TODO.
- [ ] `source_type: "file"` is modeled but yields empty rows until Feature 1 ingestion lands.

## Feature 1 — CSV / XLSX sources (the N=1 slice) — BACKEND DONE

- [x] Parsing service `services/reports/ingest.py`: csv + `pandas`/`openpyxl` for xlsx →
      rows + inferred column formats (int/float/date/datetime/text) that auto-populate `columns`.
- [x] Added `pandas` / `openpyxl` / `python-multipart` to requirements.txt + pyproject.toml.
- [x] Persist the parsed dataset: `report_uploaded_datasets` table (migration `b2c3d4e5f6a7`),
      referenced by `ReportSource.file_ref`. A file source's rows = its stored dataset.
- [x] Upload endpoint `POST /reports-layering/uploads` (multipart): extension allowlist
      (.csv/.xlsx), 10 MB / 50k-row / 200-col caps, header → column-key sanitization + dedup.
      Returns `file_ref` + inferred columns + sample rows (feeds builder preview).
- [x] Dangling `file_ref` rejected at definition time (422); JSON round-trip normalizes dates/NaN.
- [x] Tests: `tests/test_ingest.py` (CSV/XLSX/dedup/caps) + upload/file-source flow + file×file join.
- [ ] Upload flow decoupled (upload → ref → reference in source). A per-source scoped upload
      endpoint could come later if the builder wants it.
- [x] Orphaned-upload GC: `datasets.delete_orphans` + admin `POST /maintenance/prune-uploads`
      (deletes uploads no source references, older than a threshold).

## Feature 3 — Builder: more controls, better visibility — IN PROGRESS

- [x] **Dry-run preview endpoint** `POST /definitions/preview`: computes real columns + sample
      rows for an unsaved definition, nothing persisted (`snapshots.preview_definition` +
      `definitions.build_preview_definition`). Frontend "Preview data" button feeds the live
      right-pane renderer with real rows instead of `mockPreviewRows()`.
- [x] Source-type selector + per-source editor cards + file-upload input + combine configurator
      (join left/right/keys/how, or union+distinct) — `components/reports/SourceEditor.tsx`,
      wired into `UploadView.tsx` behind a Single-SQL / Multiple-sources toggle. Legacy path kept.
- [x] `uploadDataset` (multipart) + `previewDefinition` API clients; new frontend types
      (SourceInput/CombineSpec/UploadedDataset/PreviewResult).
- [x] Preview surfaces backend 422s (SQL guard, undeclared params, bad file_ref) inline.
- [x] Structured metadata editors — `components/reports/MetadataEditor.tsx`: columns table
      (key/label/format/align/agg/hidden), params editor (name/type/default/required), chart
      builder (type + x picker + y-series checkboxes from detected columns). Raw JSON demoted to
      a collapsible "Advanced" `<details>`; still the source of truth (buildInput parses `meta`).
      Extra column hints (bar/heat/badge/group) remain JSON-only by design.
- [x] Preview LIMIT pushed into live SQL (wrap in `SELECT * FROM (<sql>) LIMIT n`), plus a
      post-hoc `rows[:50]` safety net for mock/file rows.
- [x] Author polish: unsaved-changes guard (beforeunload + Cancel/Back confirm via a form
      signature vs baseline) in `UploadView.tsx`.
- [x] N-way joins: SourceEditor edits a full list of joins (add/remove/edit each), applied
      left-to-right by the backend.
- [x] Per-field inline help across SourceEditor / MetadataEditor / builder sections.

## Cross-cutting

- [x] `contracts/api-contract.md` now documents the real data plane: viewer/author endpoints,
      the sources/combine definition shape, `POST /uploads`, and `POST /definitions/preview`.
      `feature-manifest.json` needs no change (no new permissions/events).
- [x] `backend/tests/test_reports_flow.py` extended: multi-source blend, file ingest, dry-run
      preview; plus `test_blend.py` and `test_ingest.py` unit suites.
- [x] Events wired: `report-published` (on create/update) and `snapshot-refreshed` (on every
      refresh) emitted via `events/reports_events.py`, with `source_count`/`source_types`/
      `has_combine` payloads. Publisher emits to the structured logger (swap the body for a real
      transport later); event contract JSON schemas + log formatter updated; test asserts emission.
