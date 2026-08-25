"""Scored H3 cells — the actual leads."""

from __future__ import annotations

import uuid

from geoalchemy2 import Geometry
from sqlalchemy import (
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.platform.database.base import Base


class HexCell(Base):
    """One H3 cell's score within one search.

    Per-search rather than global: scores are relative to the search's area
    (a "high traffic" cell in rural Montana is not one in Manhattan), and the
    weights are tunable per search. The same h3_index can therefore appear
    under several searches with different scores.
    """

    __tablename__ = "hex_cells"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    search_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("lead_searches.id", ondelete="CASCADE"), nullable=False
    )

    # H3 indexes are 15 hex chars at res<=15; stored as text for portability.
    h3_index: Mapped[str] = mapped_column(String(20), nullable=False)
    resolution: Mapped[int] = mapped_column(Integer, nullable=False)

    geometry: Mapped[object] = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326, spatial_index=False),
        nullable=False,
    )
    centroid: Mapped[object] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )

    # The headline opportunity score and its rank within this search.
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rank: Mapped[int | None] = mapped_column(Integer)

    # The four model terms, stored so the drill-down can explain *why* a cell
    # scored — an unexplained lead is not actionable.
    traffic_proxy: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    demand: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    saturation: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    anchor_pull: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Raw inputs behind the terms (POI counts by category, tract values, the
    # weights used). Free-form because the model is still being tuned.
    score_breakdown: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )

    search: Mapped["object"] = relationship("LeadSearch", backref="cells")

    __table_args__ = (
        UniqueConstraint("search_id", "h3_index", name="uq_hex_cells_search_h3"),
        # The map viewport query: cells for a search, ranked.
        Index("ix_hex_cells_search_score", "search_id", "score"),
        Index("ix_hex_cells_search_rank", "search_id", "rank"),
        Index("ix_hex_cells_geometry", "geometry", postgresql_using="gist"),
    )
