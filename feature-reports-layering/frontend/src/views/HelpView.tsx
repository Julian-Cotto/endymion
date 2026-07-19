import type { ReactNode } from "react";
import { navigate } from "../hooks/useHashRoute";
import { GUIDE_MARKDOWN } from "./guideMarkdown";

/** Download the AI-ready spec as a Markdown file. */
function downloadAiSpec() {
  const blob = new Blob([GUIDE_MARKDOWN], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "report-builder-spec.md";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/** Inline code. */
function C({ children }: { children: ReactNode }) {
  return <code className="rl-help-code">{children}</code>;
}

/** A JSON / code block. */
function Json({ children }: { children: string }) {
  return <pre className="rl-help-json">{children}</pre>;
}

type Row = { name: string; type: string; desc: ReactNode };

function AttrTable({ rows }: { rows: Row[] }) {
  return (
    <div className="rl-help-table-wrap">
      <table className="rl-help-table">
        <thead>
          <tr>
            <th>Attribute</th>
            <th>Type / values</th>
            <th>What it does</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.name}>
              <td>
                <C>{r.name}</C>
              </td>
              <td className="rl-help-type">{r.type}</td>
              <td>{r.desc}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section id={id} className="rl-help-section">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

/** Pipeline diagram: sources → blend → snapshot → renderer. */
function DataFlow() {
  const box = (x: number, y: number, w: number, h: number) => (
    <rect x={x} y={y} width={w} height={h} rx={8} fill="rgba(127,127,127,0.08)" stroke="currentColor" />
  );
  const label = (x: number, y: number, t: string, size = 13) => (
    <text x={x} y={y} fill="currentColor" fontSize={size} textAnchor="middle">
      {t}
    </text>
  );
  return (
    <div className="rl-help-fig">
      <svg viewBox="0 0 720 190" role="img" aria-label="Sources are blended into a cached snapshot that the renderer reads">
        <defs>
          <marker id="rl-arrow" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6 Z" fill="currentColor" />
          </marker>
        </defs>
        {box(8, 18, 140, 44)}
        {label(78, 45, "SQL source")}
        {box(8, 108, 140, 44)}
        {label(78, 135, "File source")}
        {box(220, 63, 130, 44)}
        {label(285, 90, "Blend")}
        {box(420, 63, 140, 44)}
        {label(490, 84, "Snapshot")}
        {label(490, 99, "(cached rows)", 10)}
        {box(610, 46, 104, 80)}
        {label(662, 66, "Renderer", 12)}
        {label(662, 84, "table", 10)}
        {label(662, 98, "chart", 10)}
        {label(662, 112, "kpi", 10)}
        <g stroke="currentColor" fill="none">
          <line x1={150} y1={40} x2={216} y2={82} markerEnd="url(#rl-arrow)" />
          <line x1={150} y1={130} x2={216} y2={90} markerEnd="url(#rl-arrow)" />
          <line x1={352} y1={85} x2={416} y2={85} markerEnd="url(#rl-arrow)" />
          <line x1={562} y1={85} x2={606} y2={86} markerEnd="url(#rl-arrow)" />
        </g>
      </svg>
      <span className="rl-hint">
        Sources are blended into one cached snapshot; viewers read the snapshot, never live data.
      </span>
    </div>
  );
}

/** Chip illustration of join / union. */
function CombineFig() {
  return (
    <div className="rl-help-fig">
      <div className="rl-combine-fig">
        <div className="rl-chip">
          policies<small>id, premium</small>
        </div>
        <span className="rl-op">⨝ join&nbsp;on&nbsp;id</span>
        <div className="rl-chip">
          claims<small>id, paid</small>
        </div>
        <span className="rl-op">→</span>
        <div className="rl-chip rl-chip-out">
          blended<small>id, premium, paid</small>
        </div>
      </div>
      <div className="rl-combine-fig">
        <div className="rl-chip">
          east<small>region, n</small>
        </div>
        <span className="rl-op">∪ union</span>
        <div className="rl-chip">
          west<small>region, n</small>
        </div>
        <span className="rl-op">→</span>
        <div className="rl-chip rl-chip-out">
          stacked<small>region, n (all rows)</small>
        </div>
      </div>
    </div>
  );
}

export function HelpView() {
  return (
    <div className="rl-help">
      <div className="rl-help-head">
        <h1>Report Builder — Guide</h1>
        <div className="rl-actions">
          <button
            className="rl-btn"
            onClick={downloadAiSpec}
            title="Download a self-contained Markdown spec to paste into an AI assistant"
          >
            ⬇ Download for AI
          </button>
          <button className="rl-btn rl-btn-primary" onClick={() => navigate({ view: "upload" })}>
            Open the builder →
          </button>
        </div>
      </div>
      <p className="rl-hint" style={{ marginTop: -12 }}>
        “Download for AI” saves a Markdown spec of the whole definition format —
        paste it into an AI assistant and ask it to write a report definition for you.
      </p>
      <p className="rl-help-lead">
        The builder turns a data source (a SQL query and/or an uploaded spreadsheet)
        plus display metadata into a slug-routed report. Everything is rendered by a
        shared, consistent renderer (tables, charts, KPI cards). Viewers never read
        live data — they read the latest cached <strong>snapshot</strong> that is
        taken when you publish or refresh.
      </p>

      {/* -------- Contents -------- */}
      <nav className="rl-help-toc">
        {[
          ["overview", "1. How the builder works"],
          ["identity", "2. Title, description & slug"],
          ["sources", "3. Data sources (SQL & files)"],
          ["combine", "4. Combining sources (join / union)"],
          ["outputs", "5. Outputs"],
          ["columns", "6. Columns"],
          ["params", "7. Parameters"],
          ["chart", "8. Chart"],
          ["layout", "9. Page layout"],
          ["access", "10. Access groups"],
          ["preview", "11. Preview & publish"],
          ["walkthrough", "12. Worked example"],
          ["recipes", "13. Common recipes"],
          ["json", "14. Full JSON reference"],
          ["cheatsheet", "15. Advanced JSON cheatsheet"],
        ].map(([id, label]) => (
          <a key={id} href={`#/help`} onClick={() => document.getElementById(id)?.scrollIntoView()}>
            {label}
          </a>
        ))}
      </nav>

      <Section id="overview" title="1. How the builder works">
        <p>
          The builder is a split view: the <strong>form</strong> on the left, a{" "}
          <strong>live preview</strong> on the right. As you define columns and a
          chart, the preview composes the report from sample data. Click{" "}
          <strong>Preview data</strong> to run a real dry-run against your sources —
          the preview then shows actual columns and rows (badge flips to “real data”)
          and nothing is saved.
        </p>
        <p>
          Publishing creates the report and takes an immediate snapshot; editing and
          saving re-runs it. The drag divider resizes the two panes.
        </p>
        <DataFlow />
      </Section>

      <Section id="identity" title="2. Title, description & slug">
        <AttrTable
          rows={[
            {
              name: "title",
              type: "string (required)",
              desc: (
                <>
                  Display name. On create the <C>slug</C> is derived from it (e.g.{" "}
                  <C>Active Policies by Region</C> → <C>active-policies-by-region</C>).
                </>
              ),
            },
            { name: "description", type: "string", desc: "Short subtitle shown on the report and browse card." },
            {
              name: "slug",
              type: "string",
              desc: (
                <>
                  URL identity. Auto-derived from the title; stays stable when you edit
                  so existing links keep working.
                </>
              ),
            },
            {
              name: "status",
              type: `"active" | "draft" | "archived"`,
              desc: "active shows in Browse; draft is author-only; archived is hidden.",
            },
          ]}
        />
      </Section>

      <Section id="sources" title="3. Data sources (SQL & files)">
        <p>
          A report gets its rows one of two ways — <strong>Single SQL query</strong>{" "}
          (the legacy path), or <strong>Multiple sources / files</strong> that are
          blended together. Toggle between them at the top of the Data source section.
        </p>

        <h3>SQL sources</h3>
        <p>SQL must be a single read-only query:</p>
        <ul>
          <li>Must start with <C>SELECT</C> or <C>WITH … SELECT</C>.</li>
          <li>Exactly one statement (no semicolons chaining statements).</li>
          <li>
            Disallowed keywords are rejected: <C>insert, update, delete, merge, drop,
            alter, create, truncate, grant, revoke, call, exec, copy, use, set,
            begin, commit</C>, etc.
          </li>
          <li>
            Reference parameters as <C>:name</C> and declare them under{" "}
            <a href="#/help" onClick={() => document.getElementById("params")?.scrollIntoView()}>Parameters</a>.
          </li>
        </ul>

        <h3>File sources (CSV / XLSX)</h3>
        <p>
          Choose <strong>File</strong> on a source and upload a spreadsheet. It is
          parsed immediately: columns and their formats are inferred and a{" "}
          <C>file_ref</C> is stored. The file <em>is</em> the data — a file source
          shows the same rows in local and live mode.
        </p>
        <AttrTable
          rows={[
            { name: "name", type: "string (required)", desc: "Stable handle used by the combine spec (e.g. policies, claims)." },
            { name: "type", type: `"sql" | "file"`, desc: "Which kind of source this is." },
            { name: "sql", type: "string", desc: "The read-only SELECT (SQL sources)." },
            { name: "file_ref", type: "string", desc: "Handle to an uploaded dataset (file sources), returned by the upload." },
            { name: "params", type: "object", desc: "Per-source bound params (same shape as report params)." },
          ]}
        />
        <p className="rl-hint">Upload limits: .csv / .xlsx only, ≤ 10 MB, ≤ 50,000 rows, ≤ 200 columns.</p>
      </Section>

      <Section id="combine" title="4. Combining sources (join / union)">
        <p>
          With two or more sources you must choose how to combine them. Blending
          happens in-process, so you can mix SQL and file sources freely.
        </p>
        <CombineFig />

        <h3>Join</h3>
        <p>
          Merge sources on matching key columns. Add one join per pair; joins apply
          left-to-right, so a third source chains onto a source already used.
        </p>
        <AttrTable
          rows={[
            { name: "op", type: `"join"`, desc: "Selects join mode." },
            { name: "joins[]", type: "array", desc: "One or more join steps." },
            { name: "joins[].left / right", type: "source name", desc: "The two sources being joined." },
            {
              name: "joins[].on",
              type: "[[left_col, right_col], …]",
              desc: "Key column pairs to match on. Same-named keys collapse to one column; differing names keep both.",
            },
            { name: "joins[].how", type: `"inner" | "left"`, desc: "inner keeps only matches; left keeps all left rows (missing right cells become null)." },
          ]}
        />
        <Json>{`"combine": {
  "op": "join",
  "joins": [
    { "left": "policies", "right": "claims",
      "on": [["policy_id", "policy_id"]], "how": "left" }
  ]
}`}</Json>

        <h3>Union</h3>
        <p>Stack sources with compatible columns end-to-end.</p>
        <AttrTable
          rows={[
            { name: "op", type: `"union"`, desc: "Selects union mode." },
            { name: "distinct", type: "boolean", desc: "When true, drops fully-duplicate rows after stacking." },
          ]}
        />
        <Json>{`"combine": { "op": "union", "distinct": true }`}</Json>
        <p className="rl-hint">
          Column-name collisions on a join are suffixed with the right source name
          (e.g. <C>amount_claims</C>).
        </p>
      </Section>

      <Section id="outputs" title="5. Outputs">
        <p>
          <C>output_types</C> chooses which renderer surfaces appear when no page{" "}
          <a href="#/help" onClick={() => document.getElementById("layout")?.scrollIntoView()}>layout</a>{" "}
          is set:
        </p>
        <AttrTable
          rows={[
            { name: `"table"`, type: "output", desc: "The data grid with formats, bars, heat, badges, summary strip." },
            { name: `"chart"`, type: "output", desc: "A chart built from the chart config." },
            { name: `"kpi"`, type: "output", desc: "KPI cards derived from summary aggregates." },
          ]}
        />
      </Section>

      <Section id="columns" title="6. Columns">
        <p>
          The columns map (<C>{`{ column_key: { … } }`}</C>) configures how each result
          column renders. Keys match the columns your query/file returns. Basic fields
          are in the structured editor; the extra “hints” are available in Advanced
          (raw JSON) and are documented here.
        </p>
        <AttrTable
          rows={[
            { name: "label", type: "string", desc: "Header text (defaults to the column key)." },
            {
              name: "format",
              type: `"int" | "float" | "currency" | "percent" | "date" | "datetime" | "text"`,
              desc: "How values are formatted.",
            },
            { name: "align", type: `"left" | "right" | "center"`, desc: "Cell alignment (numbers usually right)." },
            { name: "hidden", type: "boolean", desc: "Keep the column in data but hide it from the table." },
            { name: "agg", type: `"sum" | "avg" | "min" | "max" | "count"`, desc: "Aggregate shown in the summary strip and used for KPI cards." },
            { name: "bar", type: "boolean", desc: "Draw an inline magnitude bar behind numeric values." },
            { name: "heat", type: `true | "reverse"`, desc: "Traffic-light color scale (high = good; reverse flips it)." },
            { name: "style", type: `"badge"`, desc: "Render values as colored pills." },
            { name: "group", type: "string", desc: "Column-group band label (e.g. group several columns under “Location”)." },
          ]}
        />
        <Json>{`"columns": {
  "region":  { "label": "Region", "group": "Location" },
  "premium": { "label": "Premium", "format": "currency",
               "align": "right", "agg": "sum", "bar": true },
  "loss_ratio": { "label": "Loss ratio", "format": "percent",
                  "heat": "reverse" },
  "tier": { "label": "Tier", "style": "badge" }
}`}</Json>
      </Section>

      <Section id="params" title="7. Parameters">
        <p>
          Parameters are bound values referenced as <C>:name</C> in SQL (never string
          interpolated). Declare each one you reference; the <C>default</C> is used
          when a caller doesn’t supply a value.
        </p>
        <AttrTable
          rows={[
            { name: "type", type: `"string" | "int" | "float" | "bool" | "date"`, desc: "Value type." },
            { name: "label", type: "string", desc: "Friendly name for UI." },
            { name: "default", type: "any", desc: "Value used when none is provided." },
            { name: "required", type: "boolean", desc: "Whether a value must be supplied." },
          ]}
        />
        <Json>{`"params": {
  "status": { "type": "string", "label": "Policy status", "default": "active" },
  "since":  { "type": "date", "required": true }
}`}</Json>
        <p className="rl-hint">
          Referencing <C>:status</C> in SQL without declaring it is rejected with a
          clear error.
        </p>
      </Section>

      <Section id="chart" title="8. Chart">
        <p>Optional chart hints. Enable the chart and pick fields from your columns.</p>
        <AttrTable
          rows={[
            { name: "type", type: `"bar" | "line" | "pie" | "area"`, desc: "Chart kind." },
            { name: "x", type: "column key", desc: "Category / x-axis column." },
            { name: "y", type: "column key | array", desc: "One or more measure columns (y-series)." },
            { name: "series", type: "column key", desc: "Optional column to split into multiple series." },
            { name: "agg", type: `"sum" | "avg"`, desc: "How to combine rows sharing an x value (default sum)." },
          ]}
        />
        <Json>{`"chart": { "type": "bar", "x": "region", "y": ["premium", "claims"], "agg": "sum" }`}</Json>
      </Section>

      <Section id="layout" title="9. Page layout">
        <p>
          Optionally compose the page into blocks on a 12-column grid. When a layout
          is present it overrides <C>output_types</C>.
        </p>
        <AttrTable
          rows={[
            { name: "type", type: `"kpi" | "chart" | "table" | "note"`, desc: "What the block renders." },
            { name: "span", type: "1–12", desc: "Grid width (12 = full row)." },
            { name: "title", type: "string", desc: "Optional block heading." },
            { name: "chart", type: "chart config", desc: "Required when type is chart (same shape as §8)." },
            { name: "text", type: "string", desc: "Markdown-ish text, used when type is note." },
          ]}
        />
        <Json>{`"layout": [
  { "type": "kpi", "span": 12 },
  { "type": "chart", "span": 8, "title": "By region",
    "chart": { "type": "bar", "x": "region", "y": "premium" } },
  { "type": "table", "span": 4, "title": "Detail" }
]`}</Json>
      </Section>

      <Section id="access" title="10. Access groups">
        <p>
          <C>access_groups</C> is a list of app-managed group slugs allowed to view the
          report. Leave it empty to make the report visible to all viewers. Groups are
          managed by admins; membership is by user key (oid or email).
        </p>
        <Json>{`"access_groups": ["underwriting", "exec"]`}</Json>
      </Section>

      <Section id="preview" title="11. Preview & publish">
        <ul>
          <li>
            <strong>Preview data</strong> runs a dry-run (bounded to ~50 rows) against
            your current sources and metadata. It persists nothing and surfaces backend
            validation errors (bad SQL, undeclared params, missing file) inline.
          </li>
          <li>
            <strong>Publish / Save changes</strong> validates, stores the definition,
            and takes a fresh snapshot immediately so the report is viewable at once.
          </li>
          <li>Leaving the builder with unsaved edits asks for confirmation.</li>
        </ul>
      </Section>

      <Section id="walkthrough" title="12. Worked example">
        <p>
          Build a <strong>Premiums vs Claims by region</strong> report from a SQL
          query and an uploaded claims spreadsheet.
        </p>
        <ol className="rl-help-steps">
          <li>
            <strong>Open the builder</strong> (Upload tab) and set a title:{" "}
            <C>Premiums vs Claims</C>. The slug becomes <C>premiums-vs-claims</C>.
          </li>
          <li>
            Under <strong>Data source</strong>, choose{" "}
            <strong>Multiple sources / files</strong>. Rename the first source{" "}
            <C>policies</C>, keep type <strong>SQL</strong>, and enter:
            <Json>{`SELECT region, policy_id, premium FROM policies`}</Json>
          </li>
          <li>
            Click <strong>+ Add source</strong>, name it <C>claims</C>, switch it to{" "}
            <strong>File</strong>, and upload <C>claims.csv</C> (columns{" "}
            <C>policy_id, paid</C>). The inferred columns appear on the card.
          </li>
          <li>
            A <strong>Combine</strong> box appears. Pick <strong>join</strong>, set{" "}
            <C>policies</C> <strong>left join</strong> <C>claims</C>, and add the key
            pair <C>policy_id = policy_id</C>.
          </li>
          <li>
            In <strong>Display metadata → Columns</strong>, add labels/formats:{" "}
            <C>premium</C> → currency + <C>agg: sum</C> + bar; <C>paid</C> → currency +{" "}
            <C>agg: sum</C>. In <strong>Chart</strong>, enable it, type{" "}
            <strong>bar</strong>, x = <C>region</C>, y = <C>premium</C> and{" "}
            <C>paid</C>.
          </li>
          <li>
            Click <strong>Preview data</strong> — the right pane shows the real blended
            rows and columns. Fix any errors it surfaces.
          </li>
          <li>
            <strong>Publish</strong>. A snapshot is taken and you land on the finished
            report.
          </li>
        </ol>
        <p>The resulting definition:</p>
        <Json>{`{
  "title": "Premiums vs Claims",
  "sources": [
    { "name": "policies", "type": "sql",
      "sql": "SELECT region, policy_id, premium FROM policies" },
    { "name": "claims", "type": "file", "file_ref": "<uploaded claims.csv>" }
  ],
  "combine": {
    "op": "join",
    "joins": [{ "left": "policies", "right": "claims",
                "on": [["policy_id", "policy_id"]], "how": "left" }]
  },
  "columns": {
    "region":  { "label": "Region" },
    "premium": { "label": "Premium", "format": "currency", "agg": "sum", "bar": true },
    "paid":    { "label": "Claims paid", "format": "currency", "agg": "sum" }
  },
  "chart": { "type": "bar", "x": "region", "y": ["premium", "paid"] },
  "output_types": ["kpi", "chart", "table"]
}`}</Json>
      </Section>

      <Section id="recipes" title="13. Common recipes">
        <h3>Grouped aggregate (single query)</h3>
        <Json>{`{
  "title": "Active Policies by Region",
  "sql_text": "SELECT region, COUNT(*) AS n FROM policies WHERE status = :status GROUP BY region",
  "params": { "status": { "type": "string", "default": "active" } },
  "columns": { "region": { "label": "Region" },
               "n": { "label": "Count", "format": "int", "agg": "sum", "bar": true } },
  "chart": { "type": "bar", "x": "region", "y": "n" }
}`}</Json>

        <h3>Enrich a query with an uploaded lookup file (join)</h3>
        <Json>{`{
  "title": "Policies with Agent Names",
  "sources": [
    { "name": "pol", "type": "sql", "sql": "SELECT agent_id, premium FROM policies" },
    { "name": "agents", "type": "file", "file_ref": "<agents.xlsx>" }
  ],
  "combine": { "op": "join",
    "joins": [{ "left": "pol", "right": "agents", "on": [["agent_id", "id"]], "how": "left" }] }
}`}</Json>

        <h3>Combine two regional extracts (union)</h3>
        <Json>{`{
  "title": "All Regions",
  "sources": [
    { "name": "east", "type": "file", "file_ref": "<east.csv>" },
    { "name": "west", "type": "file", "file_ref": "<west.csv>" }
  ],
  "combine": { "op": "union", "distinct": true }
}`}</Json>

        <h3>KPI-first dashboard layout</h3>
        <Json>{`{
  "title": "Book Overview",
  "sql_text": "SELECT region, premium, loss_ratio FROM book",
  "columns": {
    "premium": { "format": "currency", "agg": "sum" },
    "loss_ratio": { "format": "percent", "agg": "avg", "heat": "reverse" }
  },
  "layout": [
    { "type": "kpi", "span": 12 },
    { "type": "chart", "span": 7, "title": "Premium by region",
      "chart": { "type": "bar", "x": "region", "y": "premium" } },
    { "type": "table", "span": 5, "title": "Detail" }
  ]
}`}</Json>

        <h3>Heat-mapped performance table</h3>
        <Json>{`{
  "title": "Regional Performance",
  "sql_text": "SELECT region, retention, loss_ratio FROM perf",
  "columns": {
    "region": { "label": "Region", "group": "Location" },
    "retention": { "format": "percent", "heat": true, "group": "Performance" },
    "loss_ratio": { "format": "percent", "heat": "reverse", "group": "Performance" }
  }
}`}</Json>
      </Section>

      <Section id="json" title="14. Full JSON reference">
        <p>The complete definition payload, with both source styles shown:</p>
        <Json>{`{
  "title": "Blended Book",
  "description": "Premiums vs claims by region",
  "slug": "blended-book",          // optional; derived from title
  "status": "active",              // active | draft | archived

  // --- Data: EITHER a single query ...
  "sql_text": "SELECT region, COUNT(*) AS n FROM policies GROUP BY region",

  // --- ... OR multiple sources (omit sql_text):
  "sources": [
    { "name": "policies", "type": "sql",
      "sql": "SELECT region, id, premium FROM policies" },
    { "name": "claims", "type": "file", "file_ref": "<from upload>" }
  ],
  "combine": {
    "op": "join",                  // join | union
    "joins": [
      { "left": "policies", "right": "claims",
        "on": [["id", "policy_id"]], "how": "left" }
    ],
    "distinct": false              // union only
  },

  // --- Display metadata ---
  "columns": {
    "region":  { "label": "Region", "group": "Location" },
    "premium": { "label": "Premium", "format": "currency",
                 "align": "right", "agg": "sum", "bar": true },
    "loss_ratio": { "label": "Loss ratio", "format": "percent", "heat": "reverse" }
  },
  "params": {
    "status": { "type": "string", "label": "Status", "default": "active" }
  },
  "chart": { "type": "bar", "x": "region", "y": "premium", "agg": "sum" },
  "output_types": ["table", "chart", "kpi"],
  "layout": null,

  // --- Access ---
  "access_groups": ["underwriting"]
}`}</Json>
        <p className="rl-hint">
          Rules: provide <C>sql_text</C> <em>or</em> <C>sources</C> (not both);{" "}
          <C>combine</C> is required with 2+ sources; source names must be unique; SQL
          must be a single read-only SELECT with all <C>:params</C> declared.
        </p>
      </Section>

      <Section id="cheatsheet" title="15. Advanced JSON cheatsheet">
        <p>
          Every field in one place, for editing the <strong>Advanced (raw JSON)</strong>{" "}
          box directly. Comments mark which fields belong to which mode.
        </p>
        <Json>{`{
  "title": "string",                 // required
  "description": "string",
  "slug": "string",                  // optional; derived from title
  "status": "active|draft|archived",

  // ---- Data: provide sql_text OR sources (never both) ----
  "sql_text": "SELECT … single read-only SELECT",

  "sources": [
    {
      "name": "policies",            // unique handle, referenced by combine
      "type": "sql|file",
      "sql": "SELECT …",             // type=sql
      "file_ref": "<upload ref>",    // type=file (from POST /uploads)
      "params": { "…": { } },        // optional per-source params
      "sort_order": 0                // optional; ordering / union order
    }
  ],
  "combine": {                       // required when >1 source
    "op": "join|union",
    "joins": [                       // op=join (applied left→right)
      { "left": "policies", "right": "claims",
        "on": [["left_col", "right_col"]],
        "how": "inner|left" }
    ],
    "distinct": false                // op=union only
  },

  // ---- Display metadata ----
  "columns": {
    "col_key": {
      "label": "string",
      "format": "int|float|currency|percent|date|datetime|text",
      "align": "left|right|center",
      "hidden": false,
      "agg": "sum|avg|min|max|count",  // summary strip / KPI
      "bar": true,                     // inline magnitude bar
      "heat": true,                    // or "reverse"
      "style": "badge",
      "group": "band label"
    }
  },
  "params": {
    "name": {
      "type": "string|int|float|bool|date",
      "label": "string",
      "default": "any",
      "required": false
    }
  },
  "chart": {
    "type": "bar|line|pie|area",
    "x": "col_key",
    "y": "col_key | [col_key, …]",
    "series": "col_key",             // optional
    "agg": "sum|avg"                 // optional (default sum)
  },
  "output_types": ["table", "chart", "kpi"],
  "layout": [                        // optional; overrides output_types
    { "type": "kpi|chart|table|note",
      "span": 12,                    // 1–12
      "title": "string",
      "chart": { },                  // when type=chart
      "text": "string" }             // when type=note
  ],
  "access_groups": ["group-slug"]    // [] = visible to all viewers
}`}</Json>

        <h3>Enums at a glance</h3>
        <AttrTable
          rows={[
            { name: "status", type: `active · draft · archived`, desc: "Report visibility." },
            { name: "source.type", type: `sql · file`, desc: "Kind of data source." },
            { name: "combine.op", type: `join · union`, desc: "How sources merge." },
            { name: "join.how", type: `inner · left`, desc: "Join keep-policy." },
            { name: "column.format", type: `int · float · currency · percent · date · datetime · text`, desc: "Value formatting." },
            { name: "column.align", type: `left · right · center`, desc: "Cell alignment." },
            { name: "column.agg", type: `sum · avg · min · max · count`, desc: "Summary/KPI aggregate." },
            { name: "column.heat", type: `true · "reverse"`, desc: "Color scale direction." },
            { name: "column.style", type: `badge`, desc: "Pill rendering." },
            { name: "param.type", type: `string · int · float · bool · date`, desc: "Param value type." },
            { name: "chart.type", type: `bar · line · pie · area`, desc: "Chart kind." },
            { name: "chart.agg", type: `sum · avg`, desc: "Combine rows sharing an x." },
            { name: "output_types", type: `table · chart · kpi`, desc: "Renderer surfaces." },
            { name: "layout.type", type: `kpi · chart · table · note`, desc: "Block kind." },
            { name: "layout.span", type: `1 – 12`, desc: "Grid width." },
          ]}
        />

        <h3>Gotchas</h3>
        <ul>
          <li>
            <C>sql_text</C> and <C>sources</C> are mutually exclusive; <C>combine</C> is
            mandatory with 2+ sources and forbidden-to-omit for joins.
          </li>
          <li>
            <C>on</C> pairs are <C>[left_column, right_column]</C>. Same-named keys
            collapse to one output column; different names keep both.
          </li>
          <li>
            Join column collisions are suffixed with the right source name
            (<C>amount_claims</C>).
          </li>
          <li>
            <C>file_ref</C> must come from a real upload; a dangling ref is rejected at
            save.
          </li>
          <li>
            Column keys must match what the query/file returns — preview to confirm the
            real column names.
          </li>
          <li>
            SQL is a single read-only <C>SELECT</C>; every <C>:param</C> must be declared.
          </li>
        </ul>
      </Section>
    </div>
  );
}
