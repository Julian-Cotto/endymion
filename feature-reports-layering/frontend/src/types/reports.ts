// Types mirror the backend schemas (app/schemas/report.py).

export type OutputType = "table" | "chart" | "kpi";
export type ChartType = "bar" | "line" | "pie" | "area";

export interface ColumnConfig {
  label?: string;
  format?: string; // int | float | currency | percent | date | datetime | text
  align?: "left" | "right" | "center";
  hidden?: boolean;
  // ---- enterprise renderer hints (all optional) ----
  agg?: "sum" | "avg" | "min" | "max" | "count"; // summary-strip aggregate
  bar?: boolean; // inline magnitude bar (auto for measures; false to disable)
  heat?: boolean | "reverse"; // traffic-light color scale (high=good, reverse flips)
  style?: "badge"; // render values as colored pills
  group?: string; // column-group band label (e.g. "Location", "Performance")
}

export interface ChartConfig {
  type: ChartType;
  x: string;
  y: string | string[];
  series?: string;
  agg?: "sum" | "avg"; // how to combine rows sharing an x value (default sum)
}

export type ParamType = "string" | "int" | "float" | "bool" | "date";

export interface ParamSpec {
  type?: ParamType;
  label?: string;
  default?: unknown;
  required?: boolean;
}

export type SourceType = "sql" | "file";
export type JoinHow = "inner" | "left";

export interface SourceInput {
  name: string;
  type: SourceType;
  sql?: string | null; // for type "sql"
  file_ref?: string | null; // for type "file"
  params?: Record<string, unknown>;
  sort_order?: number;
}

export interface JoinInput {
  left: string; // source name
  right: string; // source name
  on: Array<[string, string]>; // [left_col, right_col] pairs
  how?: JoinHow;
}

export interface CombineSpec {
  op: "join" | "union";
  joins?: JoinInput[];
  distinct?: boolean; // union only
}

/** Result of POST /uploads — a stored dataset ready to reference from a source. */
export interface UploadedDataset {
  file_ref: string;
  filename: string;
  row_count: number;
  columns: Record<string, { label?: string; format?: string }>;
  sample_rows: Array<Record<string, unknown>>;
}

/** Result of POST /definitions/preview — dry-run columns + sample rows. */
export interface PreviewResult {
  result_columns: string[];
  rows: Array<Record<string, unknown>>;
  row_count: number;
}

export type BlockType = "kpi" | "chart" | "table" | "note";

export interface LayoutBlock {
  type: BlockType;
  span?: number; // 1–12 grid columns (default 12)
  title?: string;
  chart?: ChartConfig; // for type "chart"
  text?: string; // for type "note"
}

export interface ReportSummary {
  slug: string;
  title: string;
  description: string;
  output_types: OutputType[];
  access_groups: string[];
  status: string;
  last_snapshot_at: string | null;
  last_snapshot_status: string | null;
}

export interface ReportView {
  slug: string;
  title: string;
  description: string;
  output_types: OutputType[];
  layout?: LayoutBlock[] | null;
  columns: Record<string, ColumnConfig>;
  chart: ChartConfig | null;
  result_columns: string[];
  rows: Array<Record<string, unknown>>;
  row_count: number;
  snapshot_at: string | null;
  snapshot_status: string | null;
  stale: boolean;
}

export interface ReportDefinitionInput {
  title: string;
  description?: string;
  slug?: string;
  sql_text?: string; // legacy single source; omit/empty when using `sources`
  sources?: SourceInput[];
  combine?: CombineSpec | null;
  params?: Record<string, unknown>;
  columns?: Record<string, ColumnConfig>;
  chart?: ChartConfig | null;
  output_types?: OutputType[];
  layout?: LayoutBlock[] | null;
  access_groups?: string[];
  status?: "active" | "draft" | "archived";
}

export interface SourceOut {
  name: string;
  source_type: SourceType;
  sql_text: string | null;
  file_ref: string | null;
  params: Record<string, unknown>;
  sort_order: number;
}

export interface ReportDefinition extends ReportDefinitionInput {
  id: number;
  slug: string;
  sql_text?: string; // nullable server-side; empty string when source-based
  sources: SourceOut[];
  combine: CombineSpec | null;
  version: number;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  last_snapshot_at: string | null;
  last_snapshot_status: string | null;
}
