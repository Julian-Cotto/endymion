# Report Builder — Advanced JSON Cheatsheet

Every field in one place, for editing the **Advanced (raw JSON)** box directly.
For prose, tables, and examples see [builder-guide.md](builder-guide.md). This is
also the in-app Guide §15 (`#/help`).

## Full skeleton

```jsonc
{
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
}
```

## Enums at a glance

| Field | Values |
|---|---|
| `status` | `active` · `draft` · `archived` |
| `source.type` | `sql` · `file` |
| `combine.op` | `join` · `union` |
| `join.how` | `inner` · `left` |
| `column.format` | `int` · `float` · `currency` · `percent` · `date` · `datetime` · `text` |
| `column.align` | `left` · `right` · `center` |
| `column.agg` | `sum` · `avg` · `min` · `max` · `count` |
| `column.heat` | `true` · `"reverse"` |
| `column.style` | `badge` |
| `param.type` | `string` · `int` · `float` · `bool` · `date` |
| `chart.type` | `bar` · `line` · `pie` · `area` |
| `chart.agg` | `sum` · `avg` |
| `output_types` | `table` · `chart` · `kpi` |
| `layout.type` | `kpi` · `chart` · `table` · `note` |
| `layout.span` | `1` – `12` |

## Gotchas

- `sql_text` and `sources` are mutually exclusive; `combine` is mandatory with 2+
  sources and required for joins.
- `on` pairs are `[left_column, right_column]`. Same-named keys collapse to one
  output column; different names keep both.
- Join column collisions are suffixed with the right source name (`amount_claims`).
- `file_ref` must come from a real upload; a dangling ref is rejected at save.
- Column keys must match what the query/file returns — **Preview** to confirm the
  real column names.
- SQL is a single read-only `SELECT`; every `:param` must be declared.
