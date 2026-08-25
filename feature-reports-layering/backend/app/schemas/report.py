from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

OutputType = Literal["table", "chart", "kpi"]
ParamType = Literal["string", "int", "float", "bool", "date"]
ChartType = Literal["bar", "line", "pie", "area"]
SourceType = Literal["sql", "file"]
JoinHow = Literal["inner", "left"]


class ParamSpec(BaseModel):
    type: ParamType = "string"
    label: str | None = None
    default: Any = None
    required: bool = False


class ColumnConfig(BaseModel):
    label: str | None = None
    # int, float, currency, percent, date, datetime, text
    format: str | None = None
    align: Literal["left", "right", "center"] | None = None
    hidden: bool = False
    # ---- enterprise renderer hints (all optional) ----
    agg: Literal["sum", "avg", "min", "max", "count"] | None = None  # summary-strip aggregate
    bar: bool | None = None  # inline magnitude bar
    heat: bool | Literal["reverse"] | None = None  # traffic-light color scale
    style: Literal["badge"] | None = None  # render values as colored pills
    group: str | None = None  # column-group band label


class ChartConfig(BaseModel):
    type: ChartType = "bar"
    x: str
    y: str | list[str]
    series: str | None = None
    # how to combine rows sharing an x value in the chart (default sum)
    agg: Literal["sum", "avg"] | None = None


BlockType = Literal["kpi", "chart", "table", "note"]


class LayoutBlock(BaseModel):
    type: BlockType
    span: int = Field(default=12, ge=1, le=12)  # 12-column grid width
    title: str | None = None
    chart: ChartConfig | None = None  # required when type == "chart"
    text: str | None = None  # used when type == "note"


Cadence = Literal["hourly", "daily", "weekly", "monthly", "cron"]


class ScheduleEntry(BaseModel):
    """A saved refresh schedule. Stored + editable; no runner consumes it yet."""

    cadence: Cadence = "daily"
    time: str | None = None  # "HH:MM" for daily/weekly/monthly
    day_of_week: int | None = Field(default=None, ge=0, le=6)  # 0=Mon
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    cron: str | None = None  # raw cron when cadence == "cron"
    label: str | None = None
    enabled: bool = True


class SourceSpec(BaseModel):
    """One input feeding a report: a SQL query or an uploaded file dataset."""

    name: str = Field(min_length=1, max_length=160)
    type: SourceType = "sql"
    # Read-only SELECT for type == "sql" (validated by sql_guard in the service).
    sql: str | None = None
    # Handle to a stored uploaded dataset for type == "file".
    file_ref: str | None = None
    params: dict[str, ParamSpec] = Field(default_factory=dict)
    sort_order: int = 0

    @model_validator(mode="after")
    def _check_shape(self) -> "SourceSpec":
        if self.type == "sql" and not (self.sql and self.sql.strip()):
            raise ValueError(f"Source '{self.name}': sql is required for a SQL source.")
        if self.type == "file" and not self.file_ref:
            raise ValueError(f"Source '{self.name}': file_ref is required for a file source.")
        return self


class JoinSpec(BaseModel):
    """Join two named sources on one or more (left_col, right_col) key pairs."""

    left: str = Field(min_length=1)
    right: str = Field(min_length=1)
    on: list[tuple[str, str]] = Field(min_length=1)
    how: JoinHow = "inner"


class CombineSpec(BaseModel):
    """How to blend a report's sources into one result set."""

    op: Literal["join", "union"]
    joins: list[JoinSpec] = Field(default_factory=list)
    # union only: drop fully-duplicate rows after concatenation.
    distinct: bool = False

    @model_validator(mode="after")
    def _check_join_rules(self) -> "CombineSpec":
        if self.op == "join" and not self.joins:
            raise ValueError("combine.op 'join' requires at least one entry in joins.")
        return self


class ReportDefinitionIn(BaseModel):
    """The payload a BA uploads. `slug` is derived from title if omitted.

    A report gets its data one of two ways:
      * legacy single source: `sql_text` (no `sources`), or
      * one or more `sources` blended per `combine`.
    """

    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    slug: str | None = Field(default=None, max_length=160)
    sql: str = Field(default="", alias="sql_text")
    sources: list[SourceSpec] = Field(default_factory=list)
    combine: CombineSpec | None = None
    params: dict[str, ParamSpec] = Field(default_factory=dict)
    columns: dict[str, ColumnConfig] = Field(default_factory=dict)
    chart: ChartConfig | None = None
    output_types: list[OutputType] = Field(default_factory=lambda: ["table"])
    layout: list[LayoutBlock] | None = None
    access_groups: list[str] = Field(default_factory=list)
    status: Literal["active", "draft", "archived"] = "active"
    is_live: bool = True
    schedules: list[ScheduleEntry] = Field(default_factory=list)

    model_config = {"populate_by_name": True}

    @field_validator("output_types")
    @classmethod
    def _non_empty_outputs(cls, v: list[str]) -> list[str]:
        return v or ["table"]

    @model_validator(mode="after")
    def _check_data_source(self) -> "ReportDefinitionIn":
        has_sql = bool(self.sql and self.sql.strip())
        if self.sources:
            if has_sql:
                raise ValueError("Provide either sql_text or sources, not both.")
            names = [s.name for s in self.sources]
            if len(names) != len(set(names)):
                raise ValueError("Source names must be unique within a report.")
            if len(self.sources) > 1 and self.combine is None:
                raise ValueError("combine is required when a report has multiple sources.")
            if self.combine is not None:
                known = set(names)
                for j in self.combine.joins:
                    missing = {j.left, j.right} - known
                    if missing:
                        raise ValueError(
                            f"combine references unknown source(s): {', '.join(sorted(missing))}."
                        )
        elif not has_sql:
            raise ValueError("A report needs either sql_text or at least one source.")
        return self


class SourceOut(BaseModel):
    name: str
    source_type: str
    sql_text: str | None
    file_ref: str | None
    params: dict[str, Any]
    sort_order: int

    model_config = {"from_attributes": True}


class ReportDefinitionOut(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    sql_text: str | None
    sources: list[SourceOut] = Field(default_factory=list)
    combine: dict[str, Any] | None = None
    params: dict[str, Any]
    columns: dict[str, Any]
    chart: dict[str, Any] | None
    output_types: list[str]
    layout: list[dict[str, Any]] | None = None
    access_groups: list[str]
    status: str
    is_live: bool = True
    schedules: list[dict[str, Any]] | None = None
    version: int
    created_by: str | None
    created_at: dt.datetime
    updated_at: dt.datetime
    last_snapshot_at: dt.datetime | None = None
    last_snapshot_status: str | None = None

    model_config = {"from_attributes": True}


class ReportSummary(BaseModel):
    """Lightweight card entry for the browse grid (no SQL, no rows)."""

    slug: str
    title: str
    description: str
    output_types: list[str]
    access_groups: list[str]
    status: str
    is_live: bool = True
    last_snapshot_at: dt.datetime | None = None
    last_snapshot_status: str | None = None


class ReportView(BaseModel):
    """What the renderer consumes: metadata + latest snapshot rows."""

    slug: str
    title: str
    description: str
    output_types: list[str]
    layout: list[dict[str, Any]] | None = None
    columns: dict[str, Any]
    chart: dict[str, Any] | None
    is_live: bool = True
    schedules: list[dict[str, Any]] | None = None
    can_manage: bool = False  # owner/admin — controls the Live toggle in the UI
    result_columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    snapshot_at: dt.datetime | None
    snapshot_status: str | None
    stale: bool = False


class PreviewOut(BaseModel):
    """Dry-run result: real columns + a sample of rows, nothing persisted."""

    result_columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int


class UploadedDatasetOut(BaseModel):
    """Result of ingesting a CSV/XLSX: the ref to reference from a file source,
    plus inferred columns and a small sample for builder preview."""

    file_ref: str
    filename: str
    row_count: int
    columns: dict[str, Any]
    sample_rows: list[dict[str, Any]]


class GroupIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    slug: str | None = Field(default=None, max_length=120)
    description: str = ""


class GroupOut(BaseModel):
    id: int
    slug: str
    name: str
    description: str
    member_count: int = 0
    created_at: dt.datetime

    model_config = {"from_attributes": True}


class MembershipIn(BaseModel):
    user_key: str = Field(min_length=1, max_length=320)
    display_name: str | None = None


class MembershipOut(BaseModel):
    id: int
    group_id: int
    user_key: str
    display_name: str | None
    created_at: dt.datetime

    model_config = {"from_attributes": True}
