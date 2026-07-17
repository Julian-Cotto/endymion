from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

OutputType = Literal["table", "chart", "kpi"]
ParamType = Literal["string", "int", "float", "bool", "date"]
ChartType = Literal["bar", "line", "pie", "area"]


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


class ReportDefinitionIn(BaseModel):
    """The payload a BA uploads. `slug` is derived from title if omitted."""

    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    slug: str | None = Field(default=None, max_length=160)
    sql: str = Field(min_length=1, alias="sql_text")
    params: dict[str, ParamSpec] = Field(default_factory=dict)
    columns: dict[str, ColumnConfig] = Field(default_factory=dict)
    chart: ChartConfig | None = None
    output_types: list[OutputType] = Field(default_factory=lambda: ["table"])
    layout: list[LayoutBlock] | None = None
    access_groups: list[str] = Field(default_factory=list)
    status: Literal["active", "draft", "archived"] = "active"

    model_config = {"populate_by_name": True}

    @field_validator("output_types")
    @classmethod
    def _non_empty_outputs(cls, v: list[str]) -> list[str]:
        return v or ["table"]


class ReportDefinitionOut(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    sql_text: str
    params: dict[str, Any]
    columns: dict[str, Any]
    chart: dict[str, Any] | None
    output_types: list[str]
    layout: list[dict[str, Any]] | None = None
    access_groups: list[str]
    status: str
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
    result_columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    snapshot_at: dt.datetime | None
    snapshot_status: str | None
    stale: bool = False


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
