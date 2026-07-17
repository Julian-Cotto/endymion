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
  sql_text: string;
  params?: Record<string, unknown>;
  columns?: Record<string, ColumnConfig>;
  chart?: ChartConfig | null;
  output_types?: OutputType[];
  layout?: LayoutBlock[] | null;
  access_groups?: string[];
  status?: "active" | "draft" | "archived";
}

export interface ReportDefinition extends ReportDefinitionInput {
  id: number;
  slug: string;
  version: number;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  last_snapshot_at: string | null;
  last_snapshot_status: string | null;
}
