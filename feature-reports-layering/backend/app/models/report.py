from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.platform.database.base import Base


class ReportDefinition(Base):
    """A BA-authored report: parameterized read-only SQL + display metadata.

    The SQL is executed against Snowflake by the snapshot pipeline; viewers
    never read live Snowflake — they read the latest cached snapshot.
    """

    __tablename__ = "report_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # The logic the BA uploads.
    sql_text: Mapped[str] = mapped_column(Text, nullable=False)
    # {name: {type, default, label}} — bound params, never string-interpolated.
    params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # {column_key: {label, format, align, hidden}} — display config.
    columns: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # {type, x, y, series} | null — chart hints.
    chart: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # ["table", "chart", "kpi"] — renderer surfaces to show (legacy stacked mode).
    output_types: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # Optional block layout: [{type, span, title, chart}] flowed in a 12-col
    # grid. When present it overrides output_types for full page composition.
    layout: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # ["group-slug", ...] — app-managed groups allowed to view. [] == all viewers.
    access_groups: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[str | None] = mapped_column(String(320), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    snapshots: Mapped[list["ReportSnapshot"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ReportSnapshot(Base):
    """A cached execution of a report definition against Snowflake."""

    __tablename__ = "report_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("report_definitions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # ok | error
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ok")
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # resolved column keys in result order
    result_columns: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # list[dict] of result rows
    row_data: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # params the snapshot was run with
    params_used: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    elapsed_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    run_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )

    report: Mapped["ReportDefinition"] = relationship(back_populates="snapshots")


class Group(Base):
    """App-managed access group. Reports reference these by slug."""

    __tablename__ = "report_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    memberships: Mapped[list["GroupMembership"]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class GroupMembership(Base):
    """Assigns a user (by stable key: oid or email) to an access group."""

    __tablename__ = "report_group_memberships"
    __table_args__ = (UniqueConstraint("group_id", "user_key", name="uq_group_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("report_groups.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # normalized lower-case oid or email
    user_key: Mapped[str] = mapped_column(String(320), index=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    group: Mapped["Group"] = relationship(back_populates="memberships")
