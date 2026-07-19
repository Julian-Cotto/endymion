/**
 * Self-contained, AI-ready spec of the Report Builder's definition format.
 * Downloaded by the Guide's "Download for AI" button so a user can paste it into
 * an AI assistant and get valid report definitions back.
 *
 * Keep in sync with docs/builder-guide.md + docs/builder-json-cheatsheet.md.
 */
export const GUIDE_MARKDOWN = `# Reports Layering — Report Definition Spec (for AI assistants)

You are helping author a **report definition** for the Reports Layering feature.
A definition is a single JSON object. It is sent to \`POST /api/reports/reports-layering/definitions\`
to create a report, or to \`POST …/definitions/preview\` for a dry-run. Produce ONLY
a valid JSON object matching the schema below.

## Core rules

- A report gets its rows from **either** a single \`sql_text\` **or** a list of \`sources\` — never both.
- \`combine\` is **required** when there are 2+ sources; omit it for a single source.
- \`source[].name\` values must be unique; \`combine\` join refs must name existing sources.
- All SQL (single or per-source) must be ONE read-only \`SELECT\` (or \`WITH … SELECT\`).
  Disallowed: insert, update, delete, merge, drop, alter, create, truncate, grant,
  revoke, call, exec, copy, use, set, begin, commit, and multiple statements.
- Parameters are referenced as \`:name\` in SQL and MUST be declared in \`params\`.
- \`type: "file"\` sources reference an uploaded dataset via \`file_ref\` (obtained by
  uploading a CSV/XLSX first). If you don't have a real ref, use a SQL source instead.
- Column keys in \`columns\`/\`chart\`/\`layout\` must match the columns the query/file returns.

## Full schema (annotated)

\`\`\`jsonc
{
  "title": "string",                 // required
  "description": "string",
  "slug": "string",                  // optional; derived from title
  "status": "active|draft|archived",

  // Data: sql_text OR sources (never both)
  "sql_text": "SELECT … single read-only SELECT",

  "sources": [
    {
      "name": "policies",            // unique handle
      "type": "sql|file",
      "sql": "SELECT …",             // type=sql
      "file_ref": "<upload ref>",    // type=file
      "params": { "…": { } },        // optional per-source params
      "sort_order": 0                // optional
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

  "columns": {
    "col_key": {
      "label": "string",
      "format": "int|float|currency|percent|date|datetime|text",
      "align": "left|right|center",
      "hidden": false,
      "agg": "sum|avg|min|max|count",
      "bar": true,
      "heat": true,                  // or "reverse"
      "style": "badge",
      "group": "band label"
    }
  },
  "params": {
    "name": { "type": "string|int|float|bool|date",
              "label": "string", "default": "any", "required": false }
  },
  "chart": { "type": "bar|line|pie|area",
             "x": "col_key", "y": "col_key | [col_key, …]",
             "series": "col_key", "agg": "sum|avg" },
  "output_types": ["table", "chart", "kpi"],
  "layout": [
    { "type": "kpi|chart|table|note", "span": 12,
      "title": "string", "chart": { }, "text": "string" }
  ],
  "access_groups": ["group-slug"]    // [] = all viewers
}
\`\`\`

## Examples

### Single grouped query
\`\`\`json
{
  "title": "Active Policies by Region",
  "sql_text": "SELECT region, COUNT(*) AS n FROM policies WHERE status = :status GROUP BY region",
  "params": { "status": { "type": "string", "default": "active" } },
  "columns": { "region": { "label": "Region" },
               "n": { "label": "Count", "format": "int", "agg": "sum", "bar": true } },
  "chart": { "type": "bar", "x": "region", "y": "n" }
}
\`\`\`

### Join a SQL source with an uploaded file
\`\`\`json
{
  "title": "Premiums vs Claims",
  "sources": [
    { "name": "policies", "type": "sql",
      "sql": "SELECT region, policy_id, premium FROM policies" },
    { "name": "claims", "type": "file", "file_ref": "<uploaded claims.csv>" }
  ],
  "combine": { "op": "join",
    "joins": [{ "left": "policies", "right": "claims",
                "on": [["policy_id", "policy_id"]], "how": "left" }] },
  "columns": {
    "premium": { "label": "Premium", "format": "currency", "agg": "sum" },
    "paid": { "label": "Claims paid", "format": "currency", "agg": "sum" }
  },
  "chart": { "type": "bar", "x": "region", "y": ["premium", "paid"] }
}
\`\`\`

### Union two extracts
\`\`\`json
{
  "title": "All Regions",
  "sources": [
    { "name": "east", "type": "file", "file_ref": "<east.csv>" },
    { "name": "west", "type": "file", "file_ref": "<west.csv>" }
  ],
  "combine": { "op": "union", "distinct": true }
}
\`\`\`

## Enums

- status: active, draft, archived
- source.type: sql, file
- combine.op: join, union
- join.how: inner, left
- column.format: int, float, currency, percent, date, datetime, text
- column.align: left, right, center
- column.agg: sum, avg, min, max, count
- column.heat: true, "reverse"
- column.style: badge
- param.type: string, int, float, bool, date
- chart.type: bar, line, pie, area
- chart.agg: sum, avg
- output_types: table, chart, kpi
- layout.type: kpi, chart, table, note
- layout.span: 1–12
`;
